from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .models import DateRange, SQL_STAGE_KEYS, SQL_STAGE_SUFFIXES, SqlGenerationConfig, SqlSourceMode, PreviewPayload


def read_text_preserve_newlines(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def read_title_file_and_join_by_double_pipe(title_file_path: Path) -> str:
    with title_file_path.open("r", encoding="utf-8", newline="") as handle:
        cleaned_lines = [line.strip() for line in handle.readlines() if line.strip()]
    return "||".join(cleaned_lines)


def get_raw_sql_text(config: SqlGenerationConfig) -> str:
    if str(config.sql_source_mode) == SqlSourceMode.INLINE.value:
        return config.sql_text
    return read_text_preserve_newlines(config.sql_file)


def build_preview_payload(
    config: SqlGenerationConfig,
    *,
    raw_sql: str | None = None,
    resolved_sql: str | None = None,
    rendered_sql: str | None = None,
    now: datetime | None = None,
) -> PreviewPayload:
    """建立 GUI 預覽資料；若已經有 rendered_sql，優先重用避免重算。"""
    if raw_sql is None or resolved_sql is None or rendered_sql is None:
        calculated_raw_sql, calculated_resolved_sql, calculated_rendered_sql, _title = build_rendered_sql(
            config,
            now=now,
        )
        raw_sql = calculated_raw_sql if raw_sql is None else raw_sql
        resolved_sql = calculated_resolved_sql if resolved_sql is None else resolved_sql
        rendered_sql = calculated_rendered_sql if rendered_sql is None else rendered_sql

    return PreviewPayload(
        raw_sql=raw_sql,
        resolved_sql=resolved_sql,
        rendered_sql=rendered_sql,
    )


def resolve_date_tokens(text: str, date_range: DateRange) -> str:
    return text.replace("${startDate}", date_range.start_date).replace("${endDate}", date_range.end_date)


def escape_sql_literal(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace("'", "''")


def split_lines_preserving_separators(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    return lines if lines else [text]


def build_sql_clob_expression(sql_text: str) -> str:
    if not sql_text:
        return "to_clob('')"

    lines = split_lines_preserving_separators(sql_text)
    blocks: list[str] = []

    for start in range(0, len(lines), 10):
        block = "".join(lines[start : start + 10])
        blocks.append(f"to_clob('{escape_sql_literal(block)}')")

    return " || ".join(blocks)


def fill_manager_sql_template(
    template_content: str,
    oa_no: str,
    query_template: str,
    sql_clob_expression: str,
    content: str,
    author: str,
    title: str,
    sysdate: str,
) -> str:
    return (
        template_content.replace("${querytemplate}", escape_sql_literal(query_template))
        .replace("${oaNo}", escape_sql_literal(oa_no))
        .replace("'${sqlScript}'", sql_clob_expression)
        .replace("${content}", escape_sql_literal(content))
        .replace("${author}", escape_sql_literal(author))
        .replace("${title}", escape_sql_literal(title))
        .replace("${sysdate}", sysdate)
    )


def normalize_query_template_base(query_template: str) -> str:
    trimmed = query_template.strip()
    for suffix in SQL_STAGE_SUFFIXES.values():
        suffix_token = f"_{suffix}"
        if trimmed.endswith(suffix_token):
            return trimmed[: -len(suffix_token)]
    return trimmed


def build_stage_query_template(query_template: str, stage_key: str) -> str:
    if stage_key not in SQL_STAGE_KEYS:
        raise ValueError(f"未知 SQL 階段: {stage_key}")
    return f"{normalize_query_template_base(query_template)}_{SQL_STAGE_SUFFIXES[stage_key]}"


def build_rendered_sql(
    config: SqlGenerationConfig,
    *,
    now: datetime | None = None,
) -> tuple[str, str, str, str]:
    """resolved_sql 只給 preview 顯示；最終輸出保留日期占位符不直接寫死。"""
    raw_sql = get_raw_sql_text(config)
    resolved_sql = resolve_date_tokens(raw_sql, config.date_range)
    title = read_title_file_and_join_by_double_pipe(config.title_file)
    template_content = read_text_preserve_newlines(config.template_file)
    sysdate = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S.000000")
    sql_clob_expression = build_sql_clob_expression(raw_sql)
    rendered_sql = fill_manager_sql_template(
        template_content=template_content,
        oa_no=config.oa_no.strip(),
        query_template=config.query_template.strip(),
        sql_clob_expression=sql_clob_expression,
        content=config.content.strip(),
        author=config.author.strip(),
        title=title,
        sysdate=sysdate,
    )
    return raw_sql, resolved_sql, rendered_sql, title


def build_output_file_path(config: SqlGenerationConfig) -> Path:
    return config.output_dir / f"{config.query_template.strip()}.sql"


def build_renamed_output_file(output_file: Path) -> Path:
    stem = output_file.stem
    suffix = output_file.suffix
    counter = 1

    while True:
        candidate = output_file.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def resolve_output_file_conflict(output_file: Path, overwrite_mode: str) -> Path:
    if not output_file.exists():
        return output_file
    if overwrite_mode == "overwrite":
        return output_file
    if overwrite_mode == "rename":
        return build_renamed_output_file(output_file)
    raise FileExistsError(f"輸出檔已存在: {output_file}")
