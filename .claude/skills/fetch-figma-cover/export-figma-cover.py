#!/usr/bin/env python3
"""
export-figma-cover.py
使用 Figma REST API 匯出封面 frame 為 PNG

用法：
  python3 export-figma-cover.py <week-basename>

範例：
  python3 export-figma-cover.py week-3-march-2026
"""

import sys
import os
import json
import urllib.request
from pathlib import Path

FIGMA_FILE_KEY = "SXMTtv4SPq77S1FDYMgclr"
FIGMA_NODE_ID  = "31:13"

def main():
    if len(sys.argv) < 2:
        print("用法: python3 export-figma-cover.py <week-basename>")
        print("範例: python3 export-figma-cover.py week-3-march-2026")
        sys.exit(1)

    api_key = os.environ.get("FIGMA_API_KEY")
    if not api_key:
        print("錯誤：找不到 FIGMA_API_KEY 環境變數")
        print("請確認 ~/.claude/settings.json 中的 figma-developer MCP 設定正確")
        sys.exit(1)

    week_basename = sys.argv[1].strip()
    script_dir    = Path(__file__).parent
    output_dir    = script_dir.parent.parent.parent / "outputs" / "weekly" / "final"
    output_path   = output_dir / f"{week_basename}-cover.png"

    # Step 1: 取得 export URL
    node_id_encoded = FIGMA_NODE_ID.replace(":", "%3A")
    api_url = f"https://api.figma.com/v1/images/{FIGMA_FILE_KEY}?ids={node_id_encoded}&format=png&scale=2"

    req = urllib.request.Request(api_url, headers={"X-Figma-Token": api_key})
    print(f"正在從 Figma 取得封面匯出 URL...")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    if data.get("err"):
        print(f"錯誤：Figma API 回傳錯誤：{data['err']}")
        sys.exit(1)

    images = data.get("images", {})
    img_url = images.get(FIGMA_NODE_ID) or images.get(FIGMA_NODE_ID.replace(":", "-"))
    if not img_url:
        print(f"錯誤：找不到 node {FIGMA_NODE_ID} 的圖片 URL")
        print(f"API 回傳：{images}")
        sys.exit(1)

    # Step 2: 下載 PNG
    print(f"正在下載封面圖...")
    output_dir.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(img_url, str(output_path))
    print(f"封面圖已儲存：{output_path}")

if __name__ == "__main__":
    main()
