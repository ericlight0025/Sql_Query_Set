from __future__ import annotations

import os
import tempfile
from pathlib import Path


def _check_protected_path(target: Path, protected_paths: tuple[Path, ...]) -> None:
    for source in protected_paths:
        if target.resolve() == source.resolve() or (
            target.exists() and source.exists() and target.samefile(source)
        ):
            raise ValueError(f"輸出檔不可覆蓋輸入檔案: {source}")


def write_text_atomic(
    target: Path,
    text: str,
    *,
    overwrite_mode: str = "overwrite",
    protected_paths: tuple[Path, ...] = (),
) -> Path:
    """先完整寫入同目錄暫存檔，再以原子操作發布，避免截斷既有檔案。"""
    if overwrite_mode not in {"error", "overwrite", "rename"}:
        raise ValueError(f"未知覆寫模式: {overwrite_mode}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=target.parent,
            prefix=".ldq-", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())

        candidate = target
        counter = 0
        while True:
            _check_protected_path(candidate, protected_paths)
            if overwrite_mode == "overwrite":
                os.replace(temporary, candidate)
                return candidate
            try:
                # 硬連結只會建立新名稱；即使另一程序搶先寫入，也不會覆蓋它。
                os.link(temporary, candidate)
                return candidate
            except FileExistsError:
                if overwrite_mode != "rename":
                    raise FileExistsError(f"輸出檔已存在: {candidate}") from None
                counter += 1
                candidate = target.with_name(f"{target.stem}_{counter}{target.suffix}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
