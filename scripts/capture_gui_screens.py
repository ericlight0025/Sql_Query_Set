#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""啟動 GUI 並擷取各分頁靜態截圖（只截工具視窗）。"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import mss
import numpy as np


USER32 = ctypes.windll.user32


def find_window_handle_by_pid(pid: int) -> int:
    result: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_windows_proc(hwnd, _lparam):
        if not USER32.IsWindowVisible(hwnd):
            return True
        proc_id = ctypes.wintypes.DWORD()
        USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid:
            # 排除空標題視窗，避免抓到隱藏父容器
            length = USER32.GetWindowTextLengthW(hwnd)
            if length > 0:
                result.append(hwnd)
                return False
        return True

    USER32.EnumWindows(enum_windows_proc, 0)
    return result[0] if result else 0


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    rect = ctypes.wintypes.RECT()
    ok = USER32.GetWindowRect(hwnd, ctypes.byref(rect))
    if not ok:
        raise RuntimeError("GetWindowRect failed")
    return rect.left, rect.top, rect.right, rect.bottom


def wait_for_window(pid: int, timeout_sec: float = 20.0) -> int:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        hwnd = find_window_handle_by_pid(pid)
        if hwnd:
            return hwnd
        time.sleep(0.2)
    return 0


def capture_window(path: Path, pid: int) -> None:
    hwnd = wait_for_window(pid, timeout_sec=5.0)
    if not hwnd:
        raise RuntimeError(f"找不到 PID={pid} 的可見視窗")
    left, top, right, bottom = get_window_rect(hwnd)
    region = {
        "left": int(left),
        "top": int(top),
        "width": int(right - left),
        "height": int(bottom - top),
    }
    with mss.mss() as sct:
        frame = sct.grab(region)
    array = np.array(frame)
    bgr = cv2.cvtColor(array, cv2.COLOR_BGRA2BGR)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), bgr)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    python_exe = Path(os.environ.get("PYTHON_EXE", "")).resolve() if os.environ.get("PYTHON_EXE") else Path(sys.executable).resolve()

    env = os.environ.copy()
    env["LDQ_DEMO_AUTO"] = "1"

    proc = subprocess.Popen([str(python_exe), "gui.py"], cwd=str(root), env=env)
    try:
        if not wait_for_window(proc.pid, timeout_sec=25.0):
            raise RuntimeError("GUI 視窗啟動逾時")
        # 對應自動導覽節奏抓圖
        shots = [
            ("screen-home.png", 0.8),
            ("screen-preview-raw.png", 2.8),
            ("screen-preview-rendered.png", 2.2),
            ("screen-date-replace.png", 2.0),
            ("screen-system-settings.png", 2.2),
        ]
        for name, wait_sec in shots:
            time.sleep(wait_sec)
            capture_window(root / "docs" / "assets" / name, proc.pid)
            print(f"captured: {name}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
