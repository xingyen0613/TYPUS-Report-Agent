#!/usr/bin/env python3
"""
save-cover-from-clipboard.py
從剪貼板取得圖片並儲存為封面 PNG

用法：
  python3 save-cover-from-clipboard.py <week-basename>

範例：
  python3 save-cover-from-clipboard.py week-3-march-2026
"""

import sys
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("用法: python3 save-cover-from-clipboard.py <week-basename>")
        print("範例: python3 save-cover-from-clipboard.py week-3-march-2026")
        sys.exit(1)

    week_basename = sys.argv[1].strip()
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent.parent.parent / "outputs" / "weekly" / "final"
    output_path = output_dir / f"{week_basename}-cover.png"

    try:
        from PIL import ImageGrab
    except ImportError:
        print("錯誤：需要安裝 Pillow。請執行：pip3 install Pillow")
        sys.exit(1)

    img = ImageGrab.grabclipboard()
    if img is None:
        print("錯誤：剪貼板中沒有圖片。請先在 Figma 按 Cmd+Shift+C 複製封面 frame。")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    print(f"封面圖已儲存：{output_path}")

if __name__ == "__main__":
    main()
