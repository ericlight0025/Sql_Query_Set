from __future__ import annotations

from datetime import datetime

from .models import SqlGenerationConfig, SqlGenerationResult
from .sql_render_service import (
    build_output_file_path,
    build_renamed_output_file,
    build_rendered_sql,
    build_sql_clob_expression,
    escape_sql_literal,
    fill_manager_sql_template,
    get_raw_sql_text,
    read_text_preserve_newlines,
    read_title_file_and_join_by_double_pipe,
    resolve_date_tokens,
    resolve_output_file_conflict,
    split_lines_preserving_separators,
)
from .sql_validation_service import (
    validate_date_range,
    validate_generation_config,
    validate_query_template_filename,
    validate_template_placeholders,
)


def generate_sql_file(
    config: SqlGenerationConfig,
    *,
    now: datetime | None = None,
) -> SqlGenerationResult:
    """相容層：保留既有 API，但內部改走 validation/render 的分層實作。"""
    validate_generation_config(config)

    raw_sql, resolved_sql, rendered_sql, title = build_rendered_sql(config, now=now)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = resolve_output_file_conflict(build_output_file_path(config), str(config.overwrite_mode))

    with output_file.open("w", encoding="utf-8", newline="") as handle:
        handle.write(rendered_sql)

    sysdate = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S.000000")
    return SqlGenerationResult(
        output_file=output_file,
        raw_sql=raw_sql,
        resolved_sql=resolved_sql,
        filled_content=rendered_sql,
        title=title,
        sysdate=sysdate,
    )
