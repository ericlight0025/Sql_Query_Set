from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Callable

from .log_service import write_execution_log
from .models import (
    DEFAULT_LOG_DIR,
    PreviewPayload,
    SQL_STAGE_KEYS,
    SQL_STAGE_LABELS,
    SqlGenerationConfig,
    SqlValidationIssue,
    ValidationSeverity,
    WorkflowResult,
)
from .preview_service import build_preview_payload
from .sql_service import generate_sql_file
from .sql_validation_service import collect_validation_issues

DirectoryOpener = Callable[[Path], None]


def default_directory_opener(directory: Path) -> None:
    if not hasattr(os, "startfile"):
        raise RuntimeError("目前系統不支援自動開啟資料夾")
    os.startfile(str(directory))


def execute_generation(
    config: SqlGenerationConfig,
    *,
    now: datetime | None = None,
    log_dir: Path = DEFAULT_LOG_DIR,
    directory_opener: DirectoryOpener | None = None,
) -> WorkflowResult:
    messages = ["開始執行..."]
    output_dir_opened = False
    issues = collect_validation_issues(config)

    if issues:
        messages.extend(f"✗ 驗證失敗: {issue.message}" for issue in issues)
        log_file = write_execution_log(
            config=config,
            messages=messages,
            success=False,
            output_file=None,
            error_message=issues[0].message,
            log_dir=log_dir,
            now=now,
        )
        messages.append(f"操作日誌: {log_file}")
        return WorkflowResult(
            success=False,
            messages=messages,
            log_file=log_file,
            issues=issues,
            error_message=issues[0].message,
        )

    try:
        result = generate_sql_file(config, now=now)
        preview = build_preview_payload(
            config,
            raw_sql=result.raw_sql,
            resolved_sql=result.resolved_sql,
            rendered_sql=result.filled_content,
        )
        messages.extend(
            [
                f"OA 號碼: {config.oa_no}",
                f"Query 範本: {config.query_template}",
                f"輸出路徑: {config.output_dir}",
                f"SQL 檔案: {config.sql_file}",
                f"欄位檔案: {config.title_file}",
                f"模板檔案: {config.template_file}",
                f"輸出檔案: {result.output_file}",
                "✓ 執行成功",
            ]
        )

        if config.open_output_dir:
            opener = directory_opener or default_directory_opener
            try:
                opener(config.output_dir)
                output_dir_opened = True
                messages.append(f"已開啟輸出資料夾: {config.output_dir}")
            except Exception as exc:
                messages.append(f"無法自動開啟輸出資料夾: {exc}")

        log_file = write_execution_log(
            config=config,
            messages=messages,
            success=True,
            output_file=result.output_file,
            error_message="",
            log_dir=log_dir,
            now=now,
        )
        messages.append(f"操作日誌: {log_file}")

        return WorkflowResult(
            success=True,
            messages=messages,
            log_file=log_file,
            issues=[],
            preview=preview,
            output_file=result.output_file,
            title=result.title,
            sysdate=result.sysdate,
            output_dir_opened=output_dir_opened,
            stage_previews={"update": preview},
            output_files={"update": result.output_file},
        )
    except Exception as exc:
        error_message = str(exc)
        messages.append(f"✗ 執行失敗: {error_message}")
        log_file = write_execution_log(
            config=config,
            messages=messages,
            success=False,
            output_file=None,
            error_message=error_message,
            log_dir=log_dir,
            now=now,
        )
        messages.append(f"操作日誌: {log_file}")
        return WorkflowResult(
            success=False,
            messages=messages,
            log_file=log_file,
            issues=[],
            error_message=error_message,
        )


def execute_generation_bundle(
    stage_configs: dict[str, SqlGenerationConfig],
    *,
    now: datetime | None = None,
    log_dir: Path = DEFAULT_LOG_DIR,
    directory_opener: DirectoryOpener | None = None,
) -> WorkflowResult:
    """GUI 專用：一次產出 Before / Update / After 三份 SQL。"""
    update_config = stage_configs["update"]
    messages = ["開始執行 Before / Update / After 三份 SQL..."]
    output_dir_opened = False
    output_files: dict[str, Path] = {}
    stage_previews: dict[str, PreviewPayload] = {}
    issues: list[SqlValidationIssue] = []

    for stage_key in SQL_STAGE_KEYS:
        config = stage_configs[stage_key]
        for issue in collect_validation_issues(config):
            issues.append(
                SqlValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_id=issue.rule_id,
                    message=f"{SQL_STAGE_LABELS[stage_key]}: {issue.message}",
                    line_no=issue.line_no,
                )
            )

    if issues:
        messages.extend(f"✗ 驗證失敗: {issue.message}" for issue in issues)
        log_file = write_execution_log(
            config=update_config,
            messages=messages,
            success=False,
            output_file=None,
            error_message=issues[0].message,
            log_dir=log_dir,
            now=now,
        )
        messages.append(f"操作日誌: {log_file}")
        return WorkflowResult(
            success=False,
            messages=messages,
            log_file=log_file,
            issues=issues,
            error_message=issues[0].message,
        )

    try:
        for stage_key in SQL_STAGE_KEYS:
            config = stage_configs[stage_key]
            result = generate_sql_file(config, now=now)
            preview = build_preview_payload(
                config,
                raw_sql=result.raw_sql,
                resolved_sql=result.resolved_sql,
                rendered_sql=result.filled_content,
            )
            output_files[stage_key] = result.output_file
            stage_previews[stage_key] = preview
            messages.append(f"{SQL_STAGE_LABELS[stage_key]} 輸出檔案: {result.output_file}")

        if update_config.open_output_dir:
            opener = directory_opener or default_directory_opener
            try:
                opener(update_config.output_dir)
                output_dir_opened = True
                messages.append(f"已開啟輸出資料夾: {update_config.output_dir}")
            except Exception as exc:
                messages.append(f"無法自動開啟輸出資料夾: {exc}")

        messages.append("✓ 三份 SQL 皆產出成功")
        log_file = write_execution_log(
            config=update_config,
            messages=messages,
            success=True,
            output_file=output_files.get("update"),
            error_message="",
            log_dir=log_dir,
            now=now,
        )
        messages.append(f"操作日誌: {log_file}")
        return WorkflowResult(
            success=True,
            messages=messages,
            log_file=log_file,
            issues=[],
            preview=stage_previews["update"],
            output_file=output_files["update"],
            output_dir_opened=output_dir_opened,
            stage_previews=stage_previews,
            output_files=output_files,
        )
    except Exception as exc:
        error_message = str(exc)
        messages.append(f"✗ 執行失敗: {error_message}")
        log_file = write_execution_log(
            config=update_config,
            messages=messages,
            success=False,
            output_file=output_files.get("update"),
            error_message=error_message,
            log_dir=log_dir,
            now=now,
        )
        messages.append(f"操作日誌: {log_file}")
        return WorkflowResult(
            success=False,
            messages=messages,
            log_file=log_file,
            issues=[],
            error_message=error_message,
            stage_previews=stage_previews,
            output_files=output_files,
        )
