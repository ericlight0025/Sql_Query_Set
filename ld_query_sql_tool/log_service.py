from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import DEFAULT_LOG_DIR, SqlGenerationConfig


def write_execution_log(
    *,
    config: SqlGenerationConfig,
    messages: list[str],
    success: bool,
    output_file: Path | None,
    error_message: str,
    log_dir: Path = DEFAULT_LOG_DIR,
    now: datetime | None = None,
) -> Path:
    """將每次執行摘要落地成 log，方便後續追查。"""
    timestamp = now or datetime.now()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ld_query_sql_gui.log"

    lines = [
        f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {'SUCCESS' if success else 'FAILED'}",
        f"oa_no={config.oa_no}",
        f"query_template={config.query_template}",
        f"sql_source_mode={config.sql_source_mode}",
        f"output_dir={config.output_dir}",
        f"sql_file={config.sql_file}",
        f"title_file={config.title_file}",
        f"template_file={config.template_file}",
        f"overwrite_mode={config.overwrite_mode}",
        f"open_output_dir={config.open_output_dir}",
        f"output_file={output_file or ''}",
        f"error_message={error_message}",
        "messages:",
    ]
    lines.extend(f"- {message}" for message in messages)
    lines.append("-" * 60)

    with log_file.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")

    return log_file
