from __future__ import annotations

import argparse
from typing import Sequence

from .config_service import apply_setting_overrides, build_config_from_settings, load_settings, save_settings
from .models import DEFAULT_SETTINGS_FILE, AppSettings, SqlSourceMode
from .workflow import execute_generation


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="產生 OA Query SQL 管理檔")
    parser.add_argument("--settings-file", default=str(DEFAULT_SETTINGS_FILE), help="settings.json 路徑")
    parser.add_argument("--oa-no", help="OA 號碼")
    parser.add_argument("--query-template", help="Query 範本名稱")
    parser.add_argument("--output-dir", help="輸出資料夾")
    parser.add_argument("--sql-file", help="原始 SQL 檔案")
    parser.add_argument("--sql-text", help="直接輸入的原始 SQL")
    parser.add_argument(
        "--sql-source-mode",
        choices=[mode.value for mode in SqlSourceMode],
        help="SQL 來源模式：file 或 inline",
    )
    parser.add_argument("--content", help="內容描述")
    parser.add_argument("--author", help="作者")
    parser.add_argument("--title-file", help="欄位檔案")
    parser.add_argument("--template-file", help="ManagerSql.sql 範本路徑")
    parser.add_argument("--start-date", help="開始日期，格式 YYYY-MM-DD")
    parser.add_argument("--end-date", help="結束日期，格式 YYYY-MM-DD")
    parser.add_argument("--save-settings", action="store_true", help="將此次輸入回寫到 settings.json")

    overwrite_group = parser.add_mutually_exclusive_group()
    overwrite_group.add_argument("--overwrite", action="store_true", help="同名檔直接覆寫")
    overwrite_group.add_argument("--auto-rename", action="store_true", help="同名檔自動改名")

    open_group = parser.add_mutually_exclusive_group()
    open_group.add_argument("--open-output-dir", action="store_true", help="完成後開啟輸出資料夾")
    open_group.add_argument("--no-open-output-dir", action="store_true", help="完成後不要開啟輸出資料夾")
    return parser


def build_merged_settings(args: argparse.Namespace, loaded_settings: AppSettings) -> AppSettings:
    overwrite_mode = None
    if args.overwrite:
        overwrite_mode = "overwrite"
    elif args.auto_rename:
        overwrite_mode = "rename"

    open_output_dir = None
    if args.open_output_dir:
        open_output_dir = True
    elif args.no_open_output_dir:
        open_output_dir = False

    sql_source_mode = args.sql_source_mode
    sql_text = args.sql_text
    sql_file = args.sql_file
    if sql_text is not None and sql_source_mode is None:
        sql_source_mode = SqlSourceMode.INLINE.value
    elif sql_file is not None and sql_source_mode is None:
        sql_source_mode = SqlSourceMode.FILE.value

    overrides = {
        "oa_no": args.oa_no,
        "query_template": args.query_template,
        "output_dir": args.output_dir,
        "sql_source_mode": sql_source_mode,
        "sql_file": sql_file,
        "sql_text": sql_text,
        "content": args.content,
        "author": args.author,
        "title_file": args.title_file,
        "template_file": args.template_file,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "overwrite_mode": overwrite_mode,
        "open_output_dir": open_output_dir,
    }
    merged = apply_setting_overrides(loaded_settings, overrides)

    if str(merged.sql_source_mode) == SqlSourceMode.FILE.value and sql_file is not None:
        merged = apply_setting_overrides(merged, {"sql_text": ""})
    elif str(merged.sql_source_mode) == SqlSourceMode.INLINE.value and sql_text is not None:
        merged = apply_setting_overrides(merged, {"sql_file": loaded_settings.sql_file})

    return merged


def build_runtime_settings(args: argparse.Namespace, loaded_settings: AppSettings) -> AppSettings:
    merged = build_merged_settings(args, loaded_settings)

    if merged.overwrite_mode == "prompt":
        merged = apply_setting_overrides(merged, {"overwrite_mode": "error"})

    return merged


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    settings_file = args.settings_file

    try:
        loaded_settings = load_settings(settings_file)
        merged_settings = build_merged_settings(args, loaded_settings)
        if args.save_settings:
            save_settings(merged_settings, settings_file)
        runtime_settings = build_runtime_settings(args, loaded_settings)
        config = build_config_from_settings(runtime_settings)
    except Exception as exc:
        parser.exit(1, f"初始化失敗: {exc}\n")

    result = execute_generation(config)
    for message in result.messages:
        print(message)

    return 0 if result.success else 1
