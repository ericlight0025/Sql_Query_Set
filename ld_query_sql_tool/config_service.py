from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import (
    AppSettings,
    DateRange,
    DEFAULT_SETTINGS_FILE,
    OverwriteMode,
    SqlGenerationConfig,
    SqlSourceMode,
)

VALID_OVERWRITE_MODES = {mode.value for mode in OverwriteMode}
VALID_SQL_SOURCE_MODES = {mode.value for mode in SqlSourceMode}
STRING_SETTING_FIELDS = (
    "oa_no",
    "query_template",
    "output_dir",
    "sql_file",
    "sql_text",
    "before_sql_file",
    "before_sql_text",
    "after_sql_file",
    "after_sql_text",
    "content",
    "author",
    "title_file",
    "template_file",
    "start_date",
    "end_date",
    "python_exe",
    "ui_font_size",
)


def normalize_sql_source_mode(value: object, default: SqlSourceMode = SqlSourceMode.FILE) -> SqlSourceMode:
    try:
        return SqlSourceMode(str(value))
    except ValueError:
        return default


def normalize_overwrite_mode(
    value: object,
    default: OverwriteMode = OverwriteMode.PROMPT,
) -> OverwriteMode:
    try:
        return OverwriteMode(str(value))
    except ValueError:
        return default


def load_settings(settings_file: Path = DEFAULT_SETTINGS_FILE) -> AppSettings:
    settings_path = Path(settings_file)
    if not settings_path.is_file():
        return AppSettings()

    with settings_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"設定檔格式錯誤: {settings_path}")

    defaults = AppSettings()
    normalized: dict[str, object] = {}

    for field_name in STRING_SETTING_FIELDS:
        value = payload.get(field_name, getattr(defaults, field_name))
        normalized[field_name] = "" if value is None else str(value)

    normalized["sql_source_mode"] = normalize_sql_source_mode(
        payload.get("sql_source_mode", defaults.sql_source_mode),
        defaults.sql_source_mode,
    )
    normalized["overwrite_mode"] = normalize_overwrite_mode(
        payload.get("overwrite_mode", defaults.overwrite_mode),
        defaults.overwrite_mode,
    )
    normalized["open_output_dir"] = bool(payload.get("open_output_dir", defaults.open_output_dir))

    return AppSettings(**normalized)


def save_settings(settings: AppSettings, settings_file: Path = DEFAULT_SETTINGS_FILE) -> Path:
    settings_path = Path(settings_file)
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    with settings_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(asdict(settings), handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    return settings_path


def apply_setting_overrides(settings: AppSettings, overrides: dict[str, object]) -> AppSettings:
    merged = asdict(settings)

    for key, value in overrides.items():
        if value is None:
            continue
        merged[key] = value

    merged["sql_source_mode"] = normalize_sql_source_mode(
        merged.get("sql_source_mode", settings.sql_source_mode),
        settings.sql_source_mode,
    )
    merged["overwrite_mode"] = normalize_overwrite_mode(
        merged.get("overwrite_mode", settings.overwrite_mode),
        settings.overwrite_mode,
    )
    merged["open_output_dir"] = bool(merged.get("open_output_dir", settings.open_output_dir))
    return AppSettings(**merged)


def build_config_from_settings(settings: AppSettings) -> SqlGenerationConfig:
    return SqlGenerationConfig(
        oa_no=settings.oa_no,
        query_template=settings.query_template,
        output_dir=Path(settings.output_dir),
        sql_file=Path(settings.sql_file),
        sql_source_mode=normalize_sql_source_mode(settings.sql_source_mode),
        sql_text=settings.sql_text,
        content=settings.content,
        author=settings.author,
        title_file=Path(settings.title_file),
        template_file=Path(settings.template_file),
        date_range=DateRange(start_date=settings.start_date, end_date=settings.end_date),
        overwrite_mode=normalize_overwrite_mode(settings.overwrite_mode, OverwriteMode.ERROR),
        open_output_dir=settings.open_output_dir,
    )
