from __future__ import annotations

import argparse
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from ld_query_sql_tool.cli import build_merged_settings, build_runtime_settings
from ld_query_sql_tool.config_service import build_config_from_settings, load_settings, save_settings
from ld_query_sql_tool.gui import APP_BG, SQL_PREVIEW_THEMES, SqlToolApp
from ld_query_sql_tool.models import (
    AppSettings,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SQL_FILE,
    DEFAULT_TEMPLATE_FILE,
    DEFAULT_TITLE_FILE,
    PreviewPayload,
    SqlGenerationConfig,
    SqlSourceMode,
    WorkflowResult,
)
from ld_query_sql_tool.preview_service import build_preview_payload
from ld_query_sql_tool.workflow import execute_generation


VALID_TEMPLATE_TEXT = (
    "VALUES('${oaNo}', '${sqlScript}', '${content}-(${author})', '${title}', TIMESTAMP '${sysdate}');"
)


class TestLdQuerySqlWorkflow(unittest.TestCase):
    def test_load_settings_returns_defaults_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = load_settings(Path(temp_dir) / "missing.json")
            self.assertEqual(settings.oa_no, "1141202337-00")
            self.assertEqual(settings.overwrite_mode, "prompt")
            self.assertEqual(settings.output_dir, str(DEFAULT_OUTPUT_DIR))
            self.assertEqual(settings.sql_file, str(DEFAULT_SQL_FILE))
            self.assertEqual(settings.content, "查詢內容")
            self.assertEqual(settings.author, "陳OO")
            self.assertEqual(settings.title_file, str(DEFAULT_TITLE_FILE))
            self.assertEqual(settings.template_file, str(DEFAULT_TEMPLATE_FILE))
            self.assertTrue(DEFAULT_SQL_FILE.is_file())
            self.assertTrue(DEFAULT_TITLE_FILE.is_file())
            self.assertTrue(DEFAULT_TEMPLATE_FILE.is_file())

    def test_save_settings_and_load_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            original = AppSettings(
                oa_no="OA-001",
                query_template="QUERY-001",
                output_dir="C:/temp/output",
                sql_source_mode=SqlSourceMode.INLINE,
                sql_file="C:/temp/input.sql",
                sql_text="select '${startDate}', '${endDate}' from dual;",
                content="內容",
                author="作者",
                title_file="C:/temp/title.txt",
                template_file="C:/temp/template.sql",
                start_date="2026-04-01",
                end_date="2026-04-30",
                overwrite_mode="rename",
                open_output_dir=True,
            )

            save_settings(original, settings_file)
            loaded = load_settings(settings_file)

            self.assertEqual(loaded, original)

    def test_build_runtime_settings_prefers_cli_overrides(self) -> None:
        loaded_settings = AppSettings(
            oa_no="OA-OLD",
            query_template="QUERY-OLD",
            output_dir="C:/old",
            overwrite_mode="prompt",
            open_output_dir=False,
        )
        args = argparse.Namespace(
            oa_no="OA-NEW",
            query_template="QUERY-NEW",
            output_dir="C:/new",
            sql_file=None,
            sql_text=None,
            sql_source_mode=None,
            content=None,
            author=None,
            title_file=None,
            template_file=None,
            start_date=None,
            end_date=None,
            overwrite=False,
            auto_rename=True,
            open_output_dir=True,
            no_open_output_dir=False,
        )

        runtime_settings = build_runtime_settings(args, loaded_settings)

        self.assertEqual(runtime_settings.oa_no, "OA-NEW")
        self.assertEqual(runtime_settings.query_template, "QUERY-NEW")
        self.assertEqual(runtime_settings.output_dir, "C:/new")
        self.assertEqual(runtime_settings.overwrite_mode, "rename")
        self.assertTrue(runtime_settings.open_output_dir)

    def test_build_merged_settings_switches_back_to_file_mode_when_sql_file_is_explicit(self) -> None:
        loaded_settings = AppSettings(
            sql_source_mode=SqlSourceMode.INLINE,
            sql_file="C:/old.sql",
            sql_text="select 1 from dual;",
        )
        args = argparse.Namespace(
            oa_no=None,
            query_template=None,
            output_dir=None,
            sql_file="C:/new.sql",
            sql_text=None,
            sql_source_mode=None,
            content=None,
            author=None,
            title_file=None,
            template_file=None,
            start_date=None,
            end_date=None,
            overwrite=False,
            auto_rename=False,
            open_output_dir=False,
            no_open_output_dir=False,
        )

        merged_settings = build_merged_settings(args, loaded_settings)

        self.assertEqual(str(merged_settings.sql_source_mode), SqlSourceMode.FILE.value)
        self.assertEqual(merged_settings.sql_file, "C:/new.sql")
        self.assertEqual(merged_settings.sql_text, "")

    def test_execute_generation_records_failure_in_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            log_dir = base_dir / "logs"
            config = SqlGenerationConfig(
                oa_no="OA-001",
                query_template="QUERY-001",
                output_dir=base_dir / "output",
                sql_file=base_dir / "missing.sql",
                content="內容",
                author="作者",
                title_file=base_dir / "missing-title.txt",
                template_file=base_dir / "missing-template.sql",
                overwrite_mode="overwrite",
            )

            result = execute_generation(
                config=config,
                now=datetime(2026, 4, 3, 9, 30, 0),
                log_dir=log_dir,
            )

            self.assertFalse(result.success)
            self.assertIn("SQL 檔案不存在", result.error_message)
            self.assertTrue(result.issues)
            self.assertTrue(result.log_file.exists())
            log_text = result.log_file.read_text(encoding="utf-8")
            self.assertIn("FAILED", log_text)
            self.assertIn("SQL 檔案不存在", log_text)

    def test_execute_generation_success_log_and_open_with_real_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            output_dir = base_dir / "output"
            sql_file = base_dir / "source.sql"
            title_file = base_dir / "欄位.txt"
            template_file = base_dir / "ManagerSql.sql"
            log_dir = base_dir / "logs"

            sql_file.write_text("select 1 from dual;\n", encoding="utf-8", newline="")
            title_file.write_text("欄位一\n", encoding="utf-8", newline="")
            template_file.write_text(VALID_TEMPLATE_TEXT, encoding="utf-8", newline="")

            opened_directories: list[Path] = []

            config = SqlGenerationConfig(
                oa_no="OA-001",
                query_template="QUERY-001",
                output_dir=output_dir,
                sql_file=sql_file,
                content="內容",
                author="作者",
                title_file=title_file,
                template_file=template_file,
                overwrite_mode="overwrite",
                open_output_dir=True,
            )

            result = execute_generation(
                config=config,
                now=datetime(2026, 4, 3, 10, 0, 0),
                log_dir=log_dir,
                directory_opener=lambda directory: opened_directories.append(directory),
            )

            self.assertTrue(result.success)
            self.assertTrue(result.output_file and result.output_file.exists())
            self.assertEqual(opened_directories, [output_dir])
            self.assertTrue(result.log_file.exists())
            log_text = result.log_file.read_text(encoding="utf-8")
            self.assertIn("SUCCESS", log_text)
            self.assertIn("QUERY-001", log_text)
            self.assertIn(str(result.output_file), log_text)

    def test_build_preview_payload_supports_inline_sql_and_date_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            title_file = base_dir / "欄位.txt"
            template_file = base_dir / "ManagerSql.sql"
            title_file.write_text("欄位一\n欄位二\n", encoding="utf-8", newline="")
            template_file.write_text(VALID_TEMPLATE_TEXT, encoding="utf-8", newline="")

            settings = AppSettings(
                oa_no="OA-001",
                query_template="QUERY-001",
                output_dir=str(base_dir / "output"),
                sql_source_mode=SqlSourceMode.INLINE,
                sql_file=str(base_dir / "unused.sql"),
                sql_text="select '${startDate}' as start_date, '${endDate}' as end_date from dual;\n",
                content="內容",
                author="作者",
                title_file=str(title_file),
                template_file=str(template_file),
                start_date="2026-04-01",
                end_date="2026-04-30",
                overwrite_mode="overwrite",
            )

            config = build_config_from_settings(settings)
            preview = build_preview_payload(config, now=datetime(2026, 4, 3, 10, 0, 0))

            self.assertIn("${startDate}", preview.raw_sql)
            self.assertIn("2026-04-01", preview.resolved_sql)
            self.assertIn("2026-04-30", preview.resolved_sql)
            self.assertIn(
                "to_clob('select ''2026-04-01'' as start_date, ''2026-04-30'' as end_date from dual;\n')",
                preview.rendered_sql,
            )

    def test_build_preview_payload_reuses_provided_content_without_re_render(self) -> None:
        config = build_config_from_settings(AppSettings())

        with patch("ld_query_sql_tool.preview_service.build_rendered_sql") as mocked_build:
            preview = build_preview_payload(
                config,
                raw_sql="raw",
                resolved_sql="resolved",
                rendered_sql="rendered",
            )

        mocked_build.assert_not_called()
        self.assertEqual(preview.raw_sql, "raw")
        self.assertEqual(preview.resolved_sql, "resolved")
        self.assertEqual(preview.rendered_sql, "rendered")

    def test_set_preview_content_updates_preview_tabs(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            app = SqlToolApp(root)
            preview = PreviewPayload(
                raw_sql="select * from raw_table;",
                resolved_sql="select * from resolved_table;",
                rendered_sql="insert into manager_sql values ('wrapped');",
            )

            app._set_preview_content(preview)

            raw_text = app.raw_sql_text.get("1.0", "end-1c")
            rendered_text = app.rendered_sql_text.get("1.0", "end-1c")
            self.assertEqual(raw_text, preview.raw_sql)
            self.assertEqual(rendered_text, preview.rendered_sql)
        finally:
            root.destroy()

    def test_build_settings_from_form_uses_inline_sql_when_screen_edit_mode_is_selected(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            app = SqlToolApp(root)
            app.sql_source_var.set("畫面編輯")
            app._set_text_widget_content(app.raw_sql_text, "select * from edited_sql;", editable=True)

            settings = app._build_settings_from_form()

            self.assertEqual(str(settings.sql_source_mode), SqlSourceMode.INLINE.value)
            self.assertEqual(settings.sql_text, "select * from edited_sql;")
        finally:
            root.destroy()

    def test_apply_sql_theme_only_updates_sql_widgets(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        try:
            app = SqlToolApp(root)
            app._open_preview_window("原始 SQL", "select 1 from dual;")
            preview_window, preview_text = app.preview_windows[-1]
            app._apply_sql_theme("夜幕")

            self.assertEqual(app.raw_sql_text.cget("bg"), "#0F1B24")
            self.assertEqual(app.rendered_sql_text.cget("fg"), "#E7F2F8")
            self.assertEqual(preview_text.cget("bg"), SQL_PREVIEW_THEMES["夜幕"]["background"])
            self.assertEqual(root.cget("bg"), APP_BG)
            self.assertEqual(preview_window.cget("bg"), APP_BG)
        finally:
            root.destroy()

    def test_execute_process_does_not_save_settings_when_validation_fails(self) -> None:
        app = object.__new__(SqlToolApp)
        app.is_running = False
        app.settings_file = Path("C:/temp/settings.json")
        app._clear_log = lambda: None
        app._build_settings_from_form = lambda: AppSettings()
        app._append_log = lambda _message: None

        with (
            patch("ld_query_sql_tool.gui.build_config_from_settings", side_effect=ValueError("bad input")),
            patch("ld_query_sql_tool.gui.save_settings") as save_settings_mock,
            patch("ld_query_sql_tool.gui.messagebox.showerror") as showerror_mock,
        ):
            SqlToolApp._execute_process(app)

        save_settings_mock.assert_not_called()
        showerror_mock.assert_called_once_with("執行失敗", "bad input")

    def test_handle_result_saves_settings_only_on_success(self) -> None:
        app = object.__new__(SqlToolApp)
        app.settings_file = Path("C:/temp/settings.json")
        app.base_settings = AppSettings(oa_no="OLD")
        app._append_log = lambda _message: None
        app._set_running = lambda _running: None

        result = WorkflowResult(
            success=True,
            messages=["✓ 執行成功"],
            log_file=Path("C:/temp/log.txt"),
            output_file=Path("C:/temp/output.sql"),
        )
        successful_settings = AppSettings(oa_no="NEW")

        with (
            patch("ld_query_sql_tool.gui.save_settings") as save_settings_mock,
            patch("ld_query_sql_tool.gui.messagebox.showinfo") as showinfo_mock,
            patch("ld_query_sql_tool.gui.messagebox.showerror") as showerror_mock,
        ):
            SqlToolApp._handle_result(app, result, successful_settings)

        save_settings_mock.assert_called_once_with(successful_settings, app.settings_file)
        self.assertEqual(app.base_settings, successful_settings)
        showinfo_mock.assert_called_once_with("完成", "已輸出檔案:\nC:\\temp\\output.sql")
        showerror_mock.assert_not_called()

    def test_handle_result_does_not_save_settings_on_failure(self) -> None:
        app = object.__new__(SqlToolApp)
        app.settings_file = Path("C:/temp/settings.json")
        app.base_settings = AppSettings(oa_no="OLD")
        app._append_log = lambda _message: None
        app._set_running = lambda _running: None

        result = WorkflowResult(
            success=False,
            messages=["✗ 執行失敗: boom"],
            log_file=Path("C:/temp/log.txt"),
            error_message="boom",
        )

        with (
            patch("ld_query_sql_tool.gui.save_settings") as save_settings_mock,
            patch("ld_query_sql_tool.gui.messagebox.showinfo") as showinfo_mock,
            patch("ld_query_sql_tool.gui.messagebox.showerror") as showerror_mock,
        ):
            SqlToolApp._handle_result(app, result, AppSettings(oa_no="NEW"))

        save_settings_mock.assert_not_called()
        self.assertEqual(app.base_settings.oa_no, "OLD")
        showinfo_mock.assert_not_called()
        showerror_mock.assert_called_once_with("執行失敗", "boom")


if __name__ == "__main__":
    unittest.main()
