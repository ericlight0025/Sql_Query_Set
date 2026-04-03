from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from ld_query_sql_tool.models import SqlGenerationConfig
from ld_query_sql_tool.sql_service import (
    build_sql_clob_expression,
    generate_sql_file,
    read_title_file_and_join_by_double_pipe,
)


VALID_TEMPLATE_TEXT = (
    "VALUES('${oaNo}', '${sqlScript}', '${content}-(${author})', '${title}', TIMESTAMP '${sysdate}');"
)


class TestLdQuerySqlService(unittest.TestCase):
    def test_read_title_file_and_join_by_double_pipe_ignores_empty_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            title_file = Path(temp_dir) / "欄位.txt"
            title_file.write_text("欄位A\n\n 欄位B \n", encoding="utf-8", newline="")

            result = read_title_file_and_join_by_double_pipe(title_file)

            self.assertEqual(result, "欄位A||欄位B")

    def test_build_sql_clob_expression_splits_every_ten_lines_and_escapes_quotes(self) -> None:
        sql_lines = [f"line{i}\r\n" for i in range(1, 10)]
        sql_lines.append("select 'A' from dual;\r\n")
        sql_lines.append("line11\r\n")

        result = build_sql_clob_expression("".join(sql_lines))

        self.assertEqual(result.count("to_clob("), 2)
        self.assertIn("select ''A'' from dual;\r\n", result)
        self.assertIn("to_clob('line11\r\n')", result)

    def test_generate_sql_file_writes_expected_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir))

            result = generate_sql_file(config, now=datetime(2026, 4, 3, 9, 15, 30))
            with result.output_file.open("r", encoding="utf-8", newline="") as handle:
                output_text = handle.read()

            self.assertTrue(result.output_file.exists())
            self.assertEqual(result.title, "欄位一||欄位二")
            self.assertIn("1141202337-00", output_text)
            self.assertIn("to_clob('select ''ABC'' as code from dual;\r\n')", output_text)
            self.assertIn("查詢內容-(陳OO)", output_text)
            self.assertIn("欄位一||欄位二", output_text)
            self.assertIn("2026-04-03 09:15:30.000000", output_text)

    def test_generate_sql_file_rejects_invalid_query_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir), query_template="bad:name")

            with self.assertRaisesRegex(ValueError, "非法字元"):
                generate_sql_file(config)

    def test_generate_sql_file_auto_renames_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir), overwrite_mode="rename")
            expected_output = config.output_dir / "001-ph-LDNCS2WKARDQUERY_Update.sql"
            config.output_dir.mkdir(parents=True, exist_ok=True)
            expected_output.write_text("old", encoding="utf-8", newline="")

            result = generate_sql_file(config)

            self.assertEqual(result.output_file.name, "001-ph-LDNCS2WKARDQUERY_Update_1.sql")
            self.assertTrue(result.output_file.exists())

    def test_generate_sql_file_rejects_missing_template_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._build_config(Path(temp_dir), template_text="VALUES('${oaNo}');")

            with self.assertRaisesRegex(ValueError, "模板缺少必要占位符"):
                generate_sql_file(config)

    def _build_config(
        self,
        base_dir: Path,
        *,
        query_template: str = "001-ph-LDNCS2WKARDQUERY_Update",
        overwrite_mode: str = "error",
        template_text: str = VALID_TEMPLATE_TEXT,
    ) -> SqlGenerationConfig:
        output_dir = base_dir / "output"
        sql_file = base_dir / "source.sql"
        title_file = base_dir / "欄位.txt"
        template_file = base_dir / "ManagerSql.sql"

        sql_file.write_text("select 'ABC' as code from dual;\r\n", encoding="utf-8", newline="")
        title_file.write_text("欄位一\n欄位二\n", encoding="utf-8", newline="")
        template_file.write_text(template_text, encoding="utf-8", newline="")

        return SqlGenerationConfig(
            oa_no="1141202337-00",
            query_template=query_template,
            output_dir=output_dir,
            sql_file=sql_file,
            content="查詢內容",
            author="陳OO",
            title_file=title_file,
            template_file=template_file,
            overwrite_mode=overwrite_mode,
        )


if __name__ == "__main__":
    unittest.main()
