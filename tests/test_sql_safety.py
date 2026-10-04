from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from ld_query_sql_tool.cli import main
from ld_query_sql_tool.config_service import build_config_from_settings, load_settings, save_settings
from ld_query_sql_tool.file_service import write_text_atomic
from ld_query_sql_tool.models import AppSettings, DateRange, PROJECT_ROOT, SqlGenerationConfig
from ld_query_sql_tool.sql_render_service import (
    build_sql_clob_expression, fill_manager_sql_template, replace_date_tokens,
)
from ld_query_sql_tool.sql_service import generate_sql_file
from ld_query_sql_tool.sql_validation_service import collect_validation_issues, validate_query_template_filename
from ld_query_sql_tool.workflow import execute_generation, execute_generation_bundle


TEMPLATE = "VALUES('${oaNo}', '${sqlScript}', '${content}', '${author}', '${title}', '${sysdate}');"


class TestSqlSafety(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        source = self.root / "source.sql"
        title = self.root / "title.txt"
        template = self.root / "template.sql"
        source.write_text("select '${author}' from dual;\r\n", encoding="utf-8", newline="")
        title.write_text("欄位\n", encoding="utf-8")
        template.write_text(TEMPLATE, encoding="utf-8")
        self.config = SqlGenerationConfig(
            oa_no="OA", query_template="query", output_dir=self.root / "out",
            sql_file=source, title_file=title, template_file=template,
            content="內容", author="作者",
        )

    def test_long_clob_preserves_text_and_limits_each_utf8_literal(self):
        for raw in ("A" * 10001, "漢字🙂'\r\n" * 1100, "'" * 5000):
            with self.subTest(sample=raw[:5]):
                expression = build_sql_clob_expression(raw)
                literals = re.findall(r"to_clob\('((?:[^']|'')*)'\)", expression)
                self.assertGreater(len(literals), 1)
                self.assertTrue(all(len(value.encode("utf-8")) <= 4000 for value in literals))
                self.assertEqual("".join(value.replace("''", "'") for value in literals), raw)

    def test_template_does_not_rescan_inserted_sql_or_metadata(self):
        expression = build_sql_clob_expression("select '${author}', '${title}', '${sysdate}' from dual;")
        rendered = fill_manager_sql_template(
            TEMPLATE + " '${querytemplate}'", "OA", "query", expression,
            "${author}", "${title}", "${sysdate}", "2026-10-04",
        )
        self.assertIn(expression, rendered)
        self.assertIn("'${author}', '${title}', '${sysdate}', '2026-10-04'", rendered)

    def test_date_wrappers_replace_once_without_changing_identifiers(self):
        raw = "${startDate} :startDate ?startDate? startDate ${endDate} :endDate ?endDate? endDate startDateColumn my_endDate"
        replaced, start_hits, end_hits = replace_date_tokens(raw, DateRange("2026-10-01", "2026-10-04"))
        self.assertEqual((start_hits, end_hits), (4, 4))
        self.assertEqual(replaced, " ".join(["2026-10-01"] * 4 + ["2026-10-04"] * 4 + ["startDateColumn", "my_endDate"]))

    def test_empty_dates_preserve_placeholders(self):
        raw = "select '${startDate}', :endDate from dual"
        self.assertEqual(replace_date_tokens(raw, DateRange()), (raw, 0, 0))

    def test_failed_write_preserves_existing_sql_and_cleans_temporary_file(self):
        target = self.root / "existing.sql"
        target.write_bytes(b"old\r\n")
        with patch("ld_query_sql_tool.file_service.os.fsync", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                write_text_atomic(target, "new")
        self.assertEqual(target.read_bytes(), b"old\r\n")
        self.assertEqual(list(self.root.glob(".ldq-*.tmp")), [])

    def test_failed_publish_preserves_existing_file(self):
        target = self.root / "existing.sql"
        target.write_text("old", encoding="utf-8")
        with patch("ld_query_sql_tool.file_service.os.replace", side_effect=PermissionError("locked")):
            with self.assertRaises(PermissionError):
                write_text_atomic(target, "new")
        self.assertEqual(target.read_text(), "old")
        self.assertEqual(list(self.root.glob(".ldq-*.tmp")), [])

    def test_concurrent_error_mode_has_one_winner(self):
        target = self.root / "out.sql"

        def publish(index):
            try:
                write_text_atomic(target, str(index), overwrite_mode="error")
                return index
            except FileExistsError:
                return None

        with ThreadPoolExecutor(max_workers=8) as pool:
            winners = [value for value in pool.map(publish, range(8)) if value is not None]
        self.assertEqual(len(winners), 1)
        self.assertEqual(target.read_text(), str(winners[0]))

    def test_concurrent_rename_keeps_every_complete_output(self):
        target = self.root / "out.sql"
        with ThreadPoolExecutor(max_workers=8) as pool:
            paths = list(pool.map(lambda value: write_text_atomic(target, str(value), overwrite_mode="rename"), range(8)))
        self.assertEqual(len(set(paths)), 8)
        self.assertEqual({p.read_text() for p in paths}, {str(value) for value in range(8)})
        self.assertEqual(list(self.root.glob(".ldq-*.tmp")), [])

    def test_generation_cannot_overwrite_source_template_or_title(self):
        for field_name in ("sql_file", "template_file", "title_file"):
            with self.subTest(field=field_name):
                source = getattr(self.config, field_name)
                original = source.read_bytes()
                target = self.root / f"{field_name}.sql"
                target.write_bytes(original)
                config = replace(self.config, **{field_name: target}, output_dir=self.root,
                                 query_template=field_name, overwrite_mode="overwrite")
                with self.assertRaisesRegex(ValueError, "不可覆蓋輸入"):
                    generate_sql_file(config)
                self.assertEqual(target.read_bytes(), original)

    def test_generation_cannot_overwrite_hard_link_to_source(self):
        target = self.root / "query.sql"
        os.link(self.config.sql_file, target)
        config = replace(self.config, output_dir=self.root, overwrite_mode="overwrite")
        with self.assertRaisesRegex(ValueError, "不可覆蓋輸入"):
            generate_sql_file(config)
        self.assertIn("${author}", self.config.sql_file.read_text())

    def test_template_read_errors_become_validation_issues(self):
        with patch("ld_query_sql_tool.sql_validation_service.read_text_preserve_newlines", side_effect=PermissionError("denied")):
            result = execute_generation(self.config, log_dir=self.root / "logs")
        self.assertFalse(result.success)
        self.assertEqual(result.issues[0].rule_id, "TEMPLATE_READ_FAILED")

    def test_invalid_utf8_template_is_reported(self):
        self.config.template_file.write_bytes(b"\xff")
        self.assertEqual(collect_validation_issues(self.config)[0].rule_id, "TEMPLATE_READ_FAILED")

    def test_log_failure_keeps_successful_sql_result(self):
        with patch("ld_query_sql_tool.workflow.write_execution_log", side_effect=PermissionError("denied")):
            result = execute_generation(self.config)
        self.assertTrue(result.success)
        self.assertTrue(result.output_file.is_file())
        self.assertIsNone(result.log_file)
        self.assertTrue(any("日誌無法寫入" in message for message in result.messages))

    def test_log_failure_does_not_mask_validation_error(self):
        with patch("ld_query_sql_tool.workflow.write_execution_log", side_effect=PermissionError("denied")):
            result = execute_generation(replace(self.config, oa_no=""))
        self.assertFalse(result.success)
        self.assertIn("OA 號碼", result.error_message)
        self.assertIsNone(result.log_file)

    def test_bundle_log_failure_keeps_successful_outputs(self):
        configs = {stage: replace(self.config, query_template=stage) for stage in ("before", "update", "after")}
        with patch("ld_query_sql_tool.workflow.write_execution_log", side_effect=OSError("denied")):
            result = execute_generation_bundle(configs)
        self.assertTrue(result.success)
        self.assertEqual(len(result.output_files), 3)
        self.assertIsNone(result.log_file)

    def test_bundle_missing_stage_returns_failure_without_writing_files(self):
        result = execute_generation_bundle({"update": self.config})
        self.assertFalse(result.success)
        self.assertIn("before", result.error_message)
        self.assertFalse(self.config.output_dir.exists())

    def test_bundle_duplicate_output_paths_are_rejected(self):
        configs = {stage: replace(self.config, overwrite_mode="overwrite") for stage in ("before", "update", "after")}
        result = execute_generation_bundle(configs, log_dir=self.root / "logs")
        self.assertFalse(result.success)
        self.assertEqual(result.issues[0].rule_id, "OUTPUT_CONFLICT")
        self.assertFalse(self.config.output_dir.exists())

    def test_custom_settings_location_does_not_change_path_base(self):
        settings = AppSettings(root_dir=".", sql_file=str(PROJECT_ROOT / "data/input/source.sql"))
        target = self.root / "profiles" / "custom.json"
        expected = build_config_from_settings(settings)
        save_settings(settings, target)
        loaded = load_settings(target)
        self.assertEqual(build_config_from_settings(loaded), expected)
        self.assertEqual(json.loads(target.read_text())["sql_file"], "data/input/source.sql")

    def test_failed_settings_save_keeps_original_json(self):
        target = self.root / "settings.json"
        target.write_text('{"oa_no": "OLD"}', encoding="utf-8")
        with patch("ld_query_sql_tool.file_service.os.replace", side_effect=OSError("locked")):
            with self.assertRaises(OSError):
                save_settings(AppSettings(oa_no="NEW"), target)
        self.assertEqual(json.loads(target.read_text())["oa_no"], "OLD")

    def test_cli_does_not_save_invalid_settings(self):
        with patch("ld_query_sql_tool.cli.save_settings") as save, patch("builtins.print"):
            code = main(["--settings-file", str(self.root / "missing.json"), "--query-template", "bad:name", "--save-settings"])
        self.assertEqual(code, 1)
        save.assert_not_called()

    def test_cli_module_generates_then_refuses_conflict_and_auto_renames(self):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(PROJECT_ROOT)
        environment["PYTHONIOENCODING"] = "utf-8"
        settings_file = self.root / "profile" / "settings.json"
        command = [
            sys.executable, "-m", "ld_query_sql_tool.cli",
            "--settings-file", str(settings_file), "--oa-no", "OA",
            "--query-template", "query", "--sql-file", str(self.config.sql_file),
            "--output-dir", str(self.config.output_dir), "--title-file", str(self.config.title_file),
            "--template-file", str(self.config.template_file), "--save-settings",
        ]

        def run(arguments):
            return subprocess.run(arguments, cwd=self.root, env=environment, capture_output=True,
                                  text=True, encoding="utf-8", check=False)

        successful = run(command)
        self.assertEqual(successful.returncode, 0, successful.stderr)
        self.assertIn("執行成功", successful.stdout)
        output = self.config.output_dir / "query.sql"
        original = output.read_bytes()
        self.assertIn(b"${author}", original)
        self.assertTrue(settings_file.is_file())
        conflict = run(command)
        self.assertEqual(conflict.returncode, 1)
        self.assertIn("輸出檔已存在", conflict.stdout)
        self.assertEqual(output.read_bytes(), original)
        renamed = run(command + ["--auto-rename"])
        self.assertEqual(renamed.returncode, 0, renamed.stderr)
        self.assertTrue((self.config.output_dir / "query_1.sql").is_file())

    def test_filename_rejects_control_characters(self):
        for name in ("bad\nname", "bad\x00name", "bad\tname"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "非法字元"):
                validate_query_template_filename(name)


if __name__ == "__main__":
    unittest.main()
