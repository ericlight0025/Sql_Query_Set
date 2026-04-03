from __future__ import annotations

from datetime import datetime

from .models import PreviewPayload, SqlGenerationConfig
from .sql_render_service import build_rendered_sql


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
