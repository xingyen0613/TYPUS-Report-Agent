#!/usr/bin/env python3
"""
generate-cover.py - 本地生成 Typus 封面圖，不需開啟 Figma

用法：
  # 初始設定（僅需執行一次）：
  python3 generate-cover.py --setup

  # 生成 Weekly 封面：
  python3 generate-cover.py <week-basename> "<date-string>"

  # 生成 Monthly 封面：
  python3 generate-cover.py --monthly <month-basename> "<title>" "<date>"

範例：
  python3 generate-cover.py --setup
  python3 generate-cover.py week-4-march-2026 "Mar. 23, 2026"
  python3 generate-cover.py --monthly march-2026 "Mar 2026 Report" "Apr 4, 2026"
"""

import sys
import os
import json
import urllib.request
from datetime import date
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    print("請先安裝依賴：pip install Pillow numpy")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent

# Weekly
WEEKLY_TEMPLATE_PATH  = SCRIPT_DIR / "cover-base-template.png"
WEEKLY_FIGMA_NODE     = "31:13"

# Monthly
MONTHLY_TEMPLATE_PATH = SCRIPT_DIR / "monthly-cover-base-template.png"
MONTHLY_FIGMA_NODE    = "244:53"

# Shared assets
CALENDAR_ICON_PATH = SCRIPT_DIR / "calendar-icon.png"
INTER_FONT_PATH    = SCRIPT_DIR / "Inter-Regular.ttf"
INTER_BOLD_PATH    = SCRIPT_DIR / "Inter-Bold.ttf"

FIGMA_FILE_KEY = "SXMTtv4SPq77S1FDYMgclr"

# ── Layout 常數（2x 輸出尺寸：2400×1350）──────────────────────────────────
CANVAS_W = 2400
CANVAS_H = 1350

# 日期列（weekly & monthly 相同）
# Figma 1x: calendar y=579, height=38 → center=598 → 2x: 1196
DATE_ROW_CENTER_Y = 1196
ICON_W = 78    # 39 * 2
ICON_H = 76    # 38 * 2
ICON_TEXT_GAP = 18
DATE_FONT_SIZE = 56

# 標題（monthly 用）
# Figma 1x: text y=338, height=52 → center=364 → 2x: 728
TITLE_CENTER_Y = 728
TITLE_FONT_SIZE = 110  # Figma fontSize=55 * 2x；原始字體為 PF Spekk VAR w900，此處用 Helvetica Bold 替代

# 各區域抹除範圍（2x 座標，含 padding）
DATE_ERASE  = (860, 1110, 1540, 1260)   # x1, y1, x2, y2
TITLE_ERASE = (100, 615,  2300, 840)    # x1, y1, x2, y2


def get_api_key():
    api_key = os.environ.get("FIGMA_API_KEY")
    if api_key:
        return api_key
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        data = json.loads(settings_path.read_text())
        for server in data.get("mcpServers", {}).values():
            k = server.get("env", {}).get("FIGMA_API_KEY")
            if k:
                return k
    return None


def figma_export_png(api_key, node_id, dest_path):
    node_id_enc = node_id.replace(":", "%3A")
    url = f"https://api.figma.com/v1/images/{FIGMA_FILE_KEY}?ids={node_id_enc}&format=png&scale=2"
    req = urllib.request.Request(url, headers={"X-Figma-Token": api_key})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    img_url = (data.get("images", {}).get(node_id)
               or data.get("images", {}).get(node_id.replace(":", "-")))
    if not img_url:
        raise RuntimeError(f"找不到 node {node_id} 的圖片 URL，API 回傳：{data}")
    urllib.request.urlretrieve(img_url, str(dest_path))


def erase_zones(img_arr, zones):
    """對每個矩形區域用水平漸層插值抹除文字，sample_w=40px"""
    sample_w = 40
    H, W = img_arr.shape[:2]
    for (x1, y1, x2, y2) in zones:
        for y in range(y1, y2):
            lx1 = max(0, x1 - sample_w)
            rx2 = min(W, x2 + sample_w)
            left_color  = img_arr[y, lx1:x1].mean(axis=0)
            right_color = img_arr[y, x2:rx2].mean(axis=0)
            t = np.linspace(0, 1, x2 - x1)[:, np.newaxis]
            img_arr[y, x1:x2] = (left_color + t * (right_color - left_color)).astype(np.uint8)
    return img_arr


def create_base_template(source_path, template_path, zones):
    print(f"  來源：{source_path.name}")
    img_arr = np.array(Image.open(source_path).convert("RGB"))
    H, W = img_arr.shape[:2]
    print(f"  尺寸：{W}x{H}")
    img_arr = erase_zones(img_arr, zones)
    Image.fromarray(img_arr).save(str(template_path))
    print(f"  Base template 已儲存：{template_path}")


def find_font(size, bold=False):
    candidates_bold = [
        str(INTER_BOLD_PATH),
        "/System/Library/Fonts/Helvetica.ttc",   # index=1 for bold
    ]
    candidates_regular = [
        str(INTER_FONT_PATH),
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    candidates = candidates_bold if bold else candidates_regular
    for path in candidates:
        if not Path(path).exists():
            continue
        try:
            # Helvetica.ttc: index 0=regular, 1=bold
            idx = 1 if (bold and path.endswith(".ttc")) else 0
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    print("警告：找不到 TrueType 字體")
    return ImageFont.load_default()


def draw_date_row(img, date_str):
    """在封面底部繪製 calendar icon + 日期文字"""
    W, H = img.size
    calendar = Image.open(CALENDAR_ICON_PATH).convert("RGBA")
    calendar = calendar.resize((ICON_W, ICON_H), Image.LANCZOS)

    font = find_font(DATE_FONT_SIZE)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), date_str, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    total_w = ICON_W + ICON_TEXT_GAP + text_w
    group_x = (W - total_w) // 2
    icon_x  = group_x
    icon_y  = DATE_ROW_CENTER_Y - ICON_H // 2
    text_x  = group_x + ICON_W + ICON_TEXT_GAP
    text_y  = DATE_ROW_CENTER_Y - text_h // 2 - bbox[1]

    img.paste(calendar, (icon_x, icon_y), calendar)
    draw.text((text_x, text_y), date_str, font=font, fill=(255, 255, 255, 255))


def draw_title(img, title_str):
    """在封面中央繪製月報標題（粗體）"""
    W, H = img.size
    font = find_font(TITLE_FONT_SIZE, bold=True)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), title_str, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (W - text_w) // 2 - bbox[0]
    text_y = TITLE_CENTER_Y - text_h // 2 - bbox[1]
    draw.text((text_x, text_y), title_str, font=font, fill=(255, 255, 255, 255))


# ── Weekly ────────────────────────────────────────────────────────────────────

def setup_weekly(api_key, source_path=None):
    print("正在從 Figma 下載 calendar icon...")
    figma_export_png(api_key, "31:18", CALENDAR_ICON_PATH)
    print(f"  Calendar icon 已儲存：{CALENDAR_ICON_PATH}")

    if source_path is None:
        covers = sorted(
            Path("outputs/weekly/final").glob("*-cover.png"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        if not covers:
            print("錯誤：找不到現有 weekly 封面，請指定來源：--setup <cover.png>")
            sys.exit(1)
        source_path = covers[0]
        print(f"  使用最新封面作為來源：{source_path}")

    print("正在建立 weekly base template...")
    create_base_template(source_path, WEEKLY_TEMPLATE_PATH, [DATE_ERASE])


def generate_weekly(basename, date_str, output_dir):
    if not WEEKLY_TEMPLATE_PATH.exists():
        print("錯誤：找不到 weekly base template，請先執行 --setup")
        sys.exit(1)
    if not CALENDAR_ICON_PATH.exists():
        print("錯誤：找不到 calendar icon，請先執行 --setup")
        sys.exit(1)

    img = Image.open(WEEKLY_TEMPLATE_PATH).convert("RGBA")
    draw_date_row(img, date_str)

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{basename}-cover.png"
    img.convert("RGB").save(str(out))
    print(f"Weekly 封面已生成：{out}")


# ── Monthly ───────────────────────────────────────────────────────────────────

def setup_monthly(api_key, source_path=None):
    if source_path is None:
        tmp = Path("/tmp/monthly-cover-source.png")
        print("正在從 Figma 下載 monthly 封面...")
        figma_export_png(api_key, MONTHLY_FIGMA_NODE, tmp)
        source_path = tmp
        print(f"  已下載：{tmp}")

    # calendar icon 應已由 setup_weekly 下載，否則補下載
    if not CALENDAR_ICON_PATH.exists():
        print("正在從 Figma 下載 calendar icon...")
        figma_export_png(api_key, "244:58", CALENDAR_ICON_PATH)
        print(f"  Calendar icon 已儲存：{CALENDAR_ICON_PATH}")

    print("正在建立 monthly base template...")
    create_base_template(source_path, MONTHLY_TEMPLATE_PATH, [TITLE_ERASE, DATE_ERASE])


def generate_monthly(basename, title_str, date_str, output_dir):
    if not MONTHLY_TEMPLATE_PATH.exists():
        print("錯誤：找不到 monthly base template，請先執行 --setup")
        sys.exit(1)
    if not CALENDAR_ICON_PATH.exists():
        print("錯誤：找不到 calendar icon，請先執行 --setup")
        sys.exit(1)

    img = Image.open(MONTHLY_TEMPLATE_PATH).convert("RGBA")
    draw_title(img, title_str)
    draw_date_row(img, date_str)

    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{basename}-cover.png"
    img.convert("RGB").save(str(out))
    print(f"Monthly 封面已生成：{out}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "--setup":
        api_key = get_api_key()
        if not api_key:
            print("錯誤：找不到 FIGMA_API_KEY")
            sys.exit(1)
        source = Path(args[1]) if len(args) >= 2 else None
        setup_weekly(api_key, source)
        setup_monthly(api_key)
        print("\n設定完成！")
        print('  Weekly：python3 generate-cover.py <week-basename> "<date>"')
        print('  Monthly：python3 generate-cover.py --monthly <month-basename> "<title>" "<date>"')

    elif args[0] == "--monthly":
        if len(args) < 3:
            print("用法：python3 generate-cover.py --monthly <month-basename> \"<title>\" [\"<date>\"]")
            print("      date 可省略，省略時自動使用今天日期")
            print("範例：python3 generate-cover.py --monthly march-2026 \"Mar 2026 Report\"")
            sys.exit(1)
        date_str = args[3] if len(args) >= 4 else date.today().strftime("%b %-d, %Y")
        generate_monthly(args[1], args[2], date_str, Path("outputs/monthly/final"))

    else:
        if len(args) < 1:
            print("用法：python3 generate-cover.py <week-basename> [\"<date>\"]")
            print("      date 可省略，省略時自動使用今天日期")
            print("範例：python3 generate-cover.py week-4-march-2026")
            sys.exit(1)
        date_str = args[1] if len(args) >= 2 else date.today().strftime("%b %-d, %Y")
        generate_weekly(args[0], date_str, Path("outputs/weekly/final"))


if __name__ == "__main__":
    main()
