from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_INPUT_DIR = DEFAULT_DATA_DIR / "input"
DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "output"
DEFAULT_TEMPLATE_DIR = DEFAULT_DATA_DIR / "templates"
DEFAULT_SQL_FILE = DEFAULT_INPUT_DIR / "source.sql"
DEFAULT_TITLE_FILE = DEFAULT_INPUT_DIR / "欄位.txt"
DEFAULT_TEMPLATE_FILE = DEFAULT_TEMPLATE_DIR / "ManagerSql.sql"
DEFAULT_SETTINGS_FILE = PROJECT_ROOT / "settings.json"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

SQL_STAGE_KEYS = ("before", "update", "after")
SQL_STAGE_LABELS = {
    "before": "變更前",
    "update": "變更時",
    "after": "變更後",
}
SQL_STAGE_SUFFIXES = {
    "before": "Before",
    "update": "Update",
    "after": "After",
}


class SqlSourceMode(StrEnum):
    FILE = "file"
    INLINE = "inline"


class OverwriteMode(StrEnum):
    PROMPT = "prompt"
    ERROR = "error"
    OVERWRITE = "overwrite"
    RENAME = "rename"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(slots=True)
class DateRange:
    """日期只提供 preview 顯示，不直接寫死到最終輸出 SQL。"""

    start_date: str = ""
    end_date: str = ""


@dataclass(slots=True)
class SqlValidationIssue:
    severity: ValidationSeverity
    rule_id: str
    message: str
    line_no: int | None = None


@dataclass(slots=True)
class PreviewPayload:
    """單一階段的 SQL 編輯/預覽內容。"""

    raw_sql: str
    resolved_sql: str
    rendered_sql: str


@dataclass(slots=True)
class SqlGenerationConfig:
    oa_no: str
    query_template: str
    output_dir: Path
    sql_file: Path
    content: str
    author: str
    title_file: Path
    sql_source_mode: SqlSourceMode = SqlSourceMode.FILE
    sql_text: str = ""
    template_file: Path = DEFAULT_TEMPLATE_FILE
    date_range: DateRange = field(default_factory=DateRange)
    overwrite_mode: OverwriteMode = OverwriteMode.ERROR
    open_output_dir: bool = False


@dataclass(slots=True)
class SqlGenerationResult:
    output_file: Path
    raw_sql: str
    resolved_sql: str
    filled_content: str
    title: str
    sysdate: str


@dataclass(slots=True)
class WorkflowResult:
    success: bool
    messages: list[str]
    log_file: Path
    issues: list[SqlValidationIssue] = field(default_factory=list)
    preview: PreviewPayload | None = None
    output_file: Path | None = None
    error_message: str = ""
    title: str = ""
    sysdate: str = ""
    output_dir_opened: bool = False
    stage_previews: dict[str, PreviewPayload] = field(default_factory=dict)
    output_files: dict[str, Path] = field(default_factory=dict)


@dataclass(slots=True)
class AppSettings:
    """保留 update 舊欄位，同時補 before/after，方便 GUI 漸進式升級。"""

    oa_no: str = "1141202337-00"
    query_template: str = "001-ph-LDNCS2WKARDQUERY_Update"
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    sql_source_mode: SqlSourceMode = SqlSourceMode.FILE
    sql_file: str = str(DEFAULT_SQL_FILE)
    sql_text: str = ""
    before_sql_file: str = str(DEFAULT_SQL_FILE)
    before_sql_text: str = ""
    after_sql_file: str = str(DEFAULT_SQL_FILE)
    after_sql_text: str = ""
    content: str = "查詢內容"
    author: str = "陳OO"
    title_file: str = str(DEFAULT_TITLE_FILE)
    template_file: str = str(DEFAULT_TEMPLATE_FILE)
    start_date: str = ""
    end_date: str = ""
    overwrite_mode: OverwriteMode = OverwriteMode.PROMPT
    open_output_dir: bool = False
