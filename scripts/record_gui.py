#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""錄製螢幕畫面為 mp4（適合錄製本工具 GUI 操作流程）。"""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="錄製 GUI 畫面為 mp4")
    parser.add_argument("--output", default="docs/assets/gui-demo.mp4", help="輸出 mp4 路徑")
    parser.add_argument("--seconds", type=int, default=20, help="錄製秒數")
    parser.add_argument("--fps", type=int, default=12, help="錄影 FPS")
    parser.add_argument("--monitor", type=int, default=1, help="螢幕編號（1=主螢幕）")
    parser.add_argument("--x", type=int, default=0, help="錄製區域左上角 x")
    parser.add_argument("--y", type=int, default=0, help="錄製區域左上角 y")
    parser.add_argument("--width", type=int, default=0, help="錄製區域寬度（0=整個螢幕）")
    parser.add_argument("--height", type=int, default=0, help="錄製區域高度（0=整個螢幕）")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        import cv2
        import mss
        import numpy as np
    except Exception as exc:  # pragma: no cover
        print("缺少套件，請先安裝: pip install mss opencv-python numpy")
        print(f"詳細錯誤: {exc}")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with mss.mss() as sct:
        monitors = sct.monitors
        if args.monitor < 1 or args.monitor >= len(monitors):
            print(f"無效 monitor 編號: {args.monitor}，可用範圍 1~{len(monitors)-1}")
            return 1

        mon = monitors[args.monitor]
        if args.width > 0 and args.height > 0:
            region = {
                "left": mon["left"] + args.x,
                "top": mon["top"] + args.y,
                "width": args.width,
                "height": args.height,
            }
        else:
            region = {
                "left": mon["left"],
                "top": mon["top"],
                "width": mon["width"],
                "height": mon["height"],
            }

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(output_path),
            fourcc,
            float(args.fps),
            (region["width"], region["height"]),
        )
        if not writer.isOpened():
            print(f"無法建立影片: {output_path}")
            return 1

        print(f"開始錄影: {output_path}")
        print(
            f"區域 left={region['left']} top={region['top']} "
            f"width={region['width']} height={region['height']}"
        )

        frame_interval = 1.0 / max(1, args.fps)
        deadline = time.time() + max(1, args.seconds)
        next_frame_at = time.time()

        try:
            while time.time() < deadline:
                shot = sct.grab(region)
                frame = np.array(shot)
                # mss 擷取格式為 BGRA，轉成 BGR 才能寫入 VideoWriter
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                writer.write(frame_bgr)

                next_frame_at += frame_interval
                sleep_for = next_frame_at - time.time()
                if sleep_for > 0:
                    time.sleep(sleep_for)
        finally:
            writer.release()

    print(f"錄影完成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
