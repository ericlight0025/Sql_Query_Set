from __future__ import annotations

from datetime import datetime

from .models import (
    OverwriteMode,
    SqlGenerationConfig,
    SqlSourceMode,
    SqlValidationIssue,
    ValidationSeverity,
)
from .sql_render_service import read_text_preserve_newlines


REQUIRED_TEMPLATE_TOKENS = (
    "${oaNo}",
    "'${sqlScript}'",
    "${content}",
    "${author}",
    "${title}",
    "${sysdate}",
)
INVALID_FILENAME_CHARS = set('<>:"/\\|?*')
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def validate_query_template_filename(query_template: str) -> str:
    trimmed = query_template.strip()
    if not trimmed:
        raise ValueError("Query 範本不能為空")
    if any(char in INVALID_FILENAME_CHARS for char in trimmed):
        raise ValueError(f"Query 範本包含 Windows 非法字元: {trimmed}")
    if trimmed.endswith((" ", ".")):
        raise ValueError("Query 範本不能以空白或句點結尾")

    reserved_check = trimmed.split(".")[0].upper()
    if reserved_check in WINDOWS_RESERVED_NAMES:
        raise ValueError(f"Query 範本不可使用 Windows 保留名稱: {trimmed}")

    return trimmed


def validate_template_placeholders(template_content: str) -> None:
    missing_tokens = [token for token in REQUIRED_TEMPLATE_TOKENS if token not in template_content]
    if missing_tokens:
        missing_text = ", ".join(missing_tokens)
        raise ValueError(f"模板缺少必要占位符: {missing_text}")


def validate_date_range(start_date: str, end_date: str) -> None:
    """目前先支援空值，等 GUI 日期欄位補齊後再改為必填。"""
    if not start_date and not end_date:
        return
    if not start_date or not end_date:
        raise ValueError("開始日期與結束日期必須同時提供")

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    if start > end:
        raise ValueError("開始日期不可晚於結束日期")


def _issue(rule_id: str, message: str) -> SqlValidationIssue:
    return SqlValidationIssue(
        severity=ValidationSeverity.ERROR,
        rule_id=rule_id,
        message=message,
    )


def collect_validation_issues(config: SqlGenerationConfig) -> list[SqlValidationIssue]:
    """聚合目前所有輸入驗證錯誤，供 workflow/GUI/CLI 一次顯示。"""
    issues: list[SqlValidationIssue] = []

    if not config.oa_no.strip():
        issues.append(_issue("INPUT_REQUIRED", "OA 號碼不能為空"))

    try:
        validate_query_template_filename(config.query_template)
    except ValueError as exc:
        issues.append(_issue("INPUT_INVALID", str(exc)))

    if not config.content.strip():
        issues.append(_issue("INPUT_REQUIRED", "內容不能為空"))
    if not config.author.strip():
        issues.append(_issue("INPUT_REQUIRED", "作者不能為空"))

    if str(config.overwrite_mode) not in {
        OverwriteMode.ERROR.value,
        OverwriteMode.OVERWRITE.value,
        OverwriteMode.RENAME.value,
    }:
        issues.append(_issue("INPUT_INVALID", "overwrite_mode 必須是 error、overwrite 或 rename"))

    if config.output_dir.exists() and not config.output_dir.is_dir():
        issues.append(_issue("PATH_INVALID", f"輸出路徑不可為檔案: {config.output_dir}"))

    if str(config.sql_source_mode) == SqlSourceMode.FILE.value:
        if not config.sql_file.is_file():
            issues.append(_issue("PATH_INVALID", f"SQL 檔案不存在: {config.sql_file}"))
    elif str(config.sql_source_mode) == SqlSourceMode.INLINE.value:
        if not config.sql_text.strip():
            issues.append(_issue("INPUT_REQUIRED", "直接輸入模式下 SQL 內容不能為空"))
    else:
        issues.append(_issue("INPUT_INVALID", "sql_source_mode 必須是 file 或 inline"))

    if not config.title_file.is_file():
        issues.append(_issue("PATH_INVALID", f"欄位檔案不存在: {config.title_file}"))
    if not config.template_file.is_file():
        issues.append(_issue("PATH_INVALID", f"範本檔案不存在: {config.template_file}"))

    try:
        validate_date_range(config.date_range.start_date, config.date_range.end_date)
    except ValueError as exc:
        issues.append(_issue("INPUT_INVALID", str(exc)))

    if config.template_file.is_file():
        try:
            template_content = read_text_preserve_newlines(config.template_file)
            validate_template_placeholders(template_content)
        except ValueError as exc:
            issues.append(_issue("TEMPLATE_TOKEN_MISSING", str(exc)))

    return issues


def validate_generation_config(config: SqlGenerationConfig) -> None:
    issues = collect_validation_issues(config)
    if issues:
        raise ValueError(issues[0].message)
