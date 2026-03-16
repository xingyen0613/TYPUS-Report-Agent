#!/usr/bin/env python3
"""
generate_charts.py — Typus Weekly Report Chart Generator

Generates brand-consistent data charts from sentio-data MD files.
Supports: oi-dist, pnl, liquidation, dau

Usage:
  python3 generate_charts.py                    # latest sentio file, all charts
  python3 generate_charts.py --file PATH        # specific sentio file
  python3 generate_charts.py --chart oi-dist    # specific chart only

Font strategy:
  PF Spekk VAR (subset) → used for title and token names (pure alphabetic)
  Helvetica Neue / system sans-serif → used for all text with symbols ($, %, /, etc.)
"""

import os
import re
import sys
import glob
import io
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties
import numpy as np

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..', '..'))
SENTIO_DIR   = os.path.join(PROJECT_ROOT, 'data-sources', 'sentio-data')
OUTPUTS_DIR  = os.path.join(PROJECT_ROOT, 'outputs', 'weekly', 'final')
LOGO_SVG     = os.path.join(PROJECT_ROOT, 'design_style',
                             'Typus logo_horizontal_navy_square.svg')
FONT_DIR     = os.path.expanduser('~/Library/Fonts')

# ─── Brand Colors ─────────────────────────────────────────────────────────────
C_BG    = '#FFFFFF'
C_TEXT  = '#1D252D'
C_LONG  = '#5056EA'   # Typus primary blue → Long
C_SHORT = '#E8556D'   # Coral red → Short
C_GRID  = '#E2E8F0'

# ─── Canvas ───────────────────────────────────────────────────────────────────
W, H, DPI = 1400, 640, 100

# ─── Font Setup ───────────────────────────────────────────────────────────────
# PF Spekk VAR subset: has letters + digits, missing $, %, (, ), |, /, ~, :, ·
# Strategy: brand font for alphabetic-only text; system sans-serif for data text

def _setup_fonts():
    """Register PF Spekk VAR and configure system font fallback."""
    for fname in ['PFSpekkVAR-Black-subset.otf', 'PFSpekkVAR-SemiBold-subset.otf',
                  'PFSpekkVAR-Regular-subset.otf']:
        path = os.path.join(FONT_DIR, fname)
        if os.path.exists(path):
            matplotlib.font_manager.fontManager.addfont(path)
    # System font for data text (has full ASCII including $, %, etc.)
    matplotlib.rcParams['font.sans-serif'] = [
        'Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'
    ]
    matplotlib.rcParams['font.family'] = 'sans-serif'


_setup_fonts()


def fp_brand(size, weight='black'):
    """FontProperties for PF Spekk VAR brand font (use only for alphabetic text)."""
    fname_map = {
        'black':    'PFSpekkVAR-Black-subset.otf',
        'semibold': 'PFSpekkVAR-SemiBold-subset.otf',
        'regular':  'PFSpekkVAR-Regular-subset.otf',
    }
    path = os.path.join(FONT_DIR, fname_map.get(weight, fname_map['regular']))
    if os.path.exists(path):
        return FontProperties(fname=path, size=size)
    return FontProperties(family='sans-serif', size=size)


# ─── Watermark ────────────────────────────────────────────────────────────────
def add_watermark(ax, alpha=0.08):
    """
    Add Typus SVG logo watermark (centered, opacity=alpha).
    Requires cairosvg + libcairo. Falls back to text 'TYPUS' if unavailable.
    """
    try:
        # Pre-load libcairo (Homebrew path on macOS) before importing cairosvg
        import ctypes
        for lib_path in ['/opt/homebrew/lib/libcairo.2.dylib', 'libcairo.2.dylib']:
            try:
                ctypes.cdll.LoadLibrary(lib_path)
                break
            except OSError:
                continue
        import cairosvg
        from PIL import Image
        png_bytes = cairosvg.svg2png(url=LOGO_SVG, output_width=600)
        img = Image.open(io.BytesIO(png_bytes))
        img_arr = np.array(img)
        img_w, img_h = img.width, img.height   # 600 × ~263
        x0 = (W - img_w) / 2
        y0 = (H - img_h) / 2
        ax.imshow(img_arr, extent=[x0, x0 + img_w, y0, y0 + img_h],
                  alpha=alpha, zorder=1, aspect='auto')
    except (ImportError, OSError):
        # Text fallback using brand font (pure alphabetic — safe for PF Spekk VAR)
        ax.text(W / 2, H / 2, 'TYPUS',
                ha='center', va='center', zorder=1,
                fontproperties=fp_brand(110, 'black'),
                color=C_TEXT, alpha=alpha * 0.65)


# ─── Data Parsing ─────────────────────────────────────────────────────────────
def parse_dollar(s):
    """'$1,234.56' / '-$1,234.56' → float; non-numeric string → str."""
    s = s.strip()
    neg = s.startswith('-')
    s_clean = s.lstrip('-').lstrip('$').replace(',', '')
    try:
        val = float(s_clean)
        return -val if neg else val
    except ValueError:
        return s  # e.g. 'NetShort', 'NetLong'


def _parse_day_table(raw, section_num, value_col_idx, value_parser):
    """Parse a Mon–Sun table from a numbered section. Returns list of {day, date, value}."""
    sec = re.search(rf'## {section_num}\..*?\n(.*?)(?=\n## |\Z)', raw, re.DOTALL)
    rows = []
    if not sec:
        return rows
    for line in sec.group(1).split('\n'):
        if not line.startswith('|') or '---|' in line:
            continue
        cols = [c.strip() for c in line.split('|')[1:-1]]
        if len(cols) <= value_col_idx:
            continue
        day = cols[0]
        if day in ('Day', ''):
            continue
        date  = cols[1] if len(cols) > 1 else ''
        value = value_parser(cols[value_col_idx])
        rows.append({'day': day, 'date': date, 'value': value})
    return rows


def parse_sentio(filepath):
    """Parse a sentio-data MD file; return structured dict."""
    with open(filepath, encoding='utf-8') as f:
        raw = f.read()

    data = {'filepath': filepath, 'positions': []}

    m = re.search(r'Week (\d+) (\w+ \d{4})', raw)
    if m:
        data['week_num']   = m.group(1)
        data['month_year'] = m.group(2)

    m = re.search(r'\*\*覆蓋範圍\*\*[：:]\s*(.+)', raw)
    if m:
        data['date_range'] = m.group(1).strip()

    # Section 5 — Daily P&L
    data['daily_pnl'] = _parse_day_table(raw, 5, 2, parse_dollar)

    # Section 6 — Daily Liquidation
    data['daily_liquidation'] = _parse_day_table(raw, 6, 2, parse_dollar)

    # Section 7 — Daily Active Users
    def parse_int(s):
        try:
            return int(s.replace(',', ''))
        except ValueError:
            return 0
    data['daily_dau'] = _parse_day_table(raw, 7, 2, parse_int)

    # Section 10 — OI History daily snapshot
    # Look for the "Daily OI Snapshot" subsection
    oi_snap_sec = re.search(
        r'### Daily OI Snapshot.*?\n(.*?)(?=\n###|\n## |\Z)', raw, re.DOTALL)
    oi_tokens = []
    oi_daily  = []   # list of {date, token_values: {token: float}}
    if oi_snap_sec:
        header_parsed = False
        for line in oi_snap_sec.group(1).split('\n'):
            if not line.startswith('|') or '---|' in line:
                continue
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if not cols:
                continue
            if cols[0] in ('Date', ''):
                if not header_parsed:
                    oi_tokens = cols[1:]  # e.g. ['Total', 'BTC', 'ETH', ...]
                    header_parsed = True
                continue
            date_str = cols[0]
            vals = {}
            for j, tok in enumerate(oi_tokens):
                if j + 1 < len(cols):
                    v = parse_dollar(cols[j + 1])
                    vals[tok] = float(v) if isinstance(v, float) else 0.0
            if vals:
                oi_daily.append({'date': date_str, 'token_values': vals})
    data['oi_daily']  = oi_daily
    data['oi_tokens'] = oi_tokens

    # Section 12 — Daily Total Volume
    data['daily_volume'] = _parse_day_table(raw, 12, 2, parse_dollar)

    # Section 1 — TLP Price Daily Snapshot
    # Sub-table "Daily Price Snapshot" inside Section 1
    tlp_price_sec = re.search(
        r'### Daily Price Snapshot.*?\n(.*?)(?=\n###|\n## |\Z)', raw, re.DOTALL)
    tlp_daily = []
    if tlp_price_sec:
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for line in tlp_price_sec.group(1).split('\n'):
            if not line.startswith('|') or '---|' in line:
                continue
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) < 4 or cols[0] in ('Day', ''):
                continue
            if cols[0] not in day_names:
                continue
            mltp = parse_dollar(cols[2])
            itlp = parse_dollar(cols[3])
            tlp_daily.append({
                'day':  cols[0],
                'date': cols[1],
                'mtlp': float(mltp) if isinstance(mltp, float) else None,
                'itlp': float(itlp) if isinstance(itlp, float) else None,
            })
    data['tlp_daily'] = tlp_daily

    # Section 13 — Daily Fees
    data['daily_tlp_fee']      = _parse_day_table(raw, 13, 2, parse_dollar)
    data['daily_protocol_fee'] = _parse_day_table(raw, 13, 3, parse_dollar)

    # Section 8 — Opening Positions
    sec = re.search(r'## 8\..*?\n(.*?)(?=\n## |\Z)', raw, re.DOTALL)
    if sec:
        for line in sec.group(1).split('\n'):
            if not line.startswith('|') or '---|' in line or 'Token' in line:
                continue
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) < 6:
                continue
            token = cols[0]
            if token == 'ALL':
                continue
            oi    = parse_dollar(cols[1])
            long_ = parse_dollar(cols[2])
            short = parse_dollar(cols[3])
            ls    = cols[5]
            if isinstance(oi, float) and oi > 0:
                data['positions'].append({
                    'token': token,
                    'oi':    oi,
                    'long':  float(long_) if isinstance(long_, float) else 0.0,
                    'short': float(short) if isinstance(short, float) else 0.0,
                    'ls':    ls,
                })
        data['positions'].sort(key=lambda x: x['oi'], reverse=True)

    return data


# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt_k(v):
    """Format USD value: $1.2K or $950"""
    return f'${v / 1000:.1f}K' if v >= 1000 else f'${v:.0f}'


# ─── Chart: OI Distribution ───────────────────────────────────────────────────
def chart_oi_distribution(data, output_path):
    """
    Horizontal stacked bar chart: OI by token with Long/Short split + L/S ratio.

    Bar width  = token OI / max token OI (relative size)
    Color split = Long (blue) + Short (coral), proportional to L/S composition
    """
    positions = data.get('positions', [])[:5]   # top 5 by OI
    if not positions:
        print('⚠️  No position data — skipping OI Distribution chart')
        return

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=C_BG)
    ax  = fig.add_axes([0, 0, 1, 1], facecolor=C_BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')

    add_watermark(ax, alpha=0.08)

    # ── Layout (px) ───────────────────────────────────────────────────────────
    TITLE_Y    = H - 58       # 58px from top → gives ~24px breathing room above title
    PLOT_TOP   = TITLE_Y - 52
    PLOT_BOT   = 120          # increased bottom band
    LEG_Y_VAL  = PLOT_BOT - 14   # legend just below bars
    STATS_Y    = 52           # key stats — below legend (no overlap)
    SOURCE_Y   = 20

    LABEL_X = 148
    BAR_L   = 162
    BAR_R   = 1060
    BAR_W   = BAR_R - BAR_L   # 898 px
    VALUE_X = BAR_R + 16
    LS_X    = W - 24

    # ── Title — PF Spekk VAR Black (pure alphabetic) ──────────────────────────
    ax.text(W / 2, TITLE_Y, 'OI Distribution',
            ha='center', va='bottom', zorder=5,
            fontproperties=fp_brand(34, 'black'), color=C_TEXT)

    # ── Column headers — system font ──────────────────────────────────────────
    HEADER_Y = PLOT_TOP + 6
    for x, s, align in [(LABEL_X, 'Market', 'right'),
                         (VALUE_X, 'OI  (Share)', 'left'),
                         (LS_X,   'L/S Ratio', 'right')]:
        ax.text(x, HEADER_Y, s, ha=align, va='bottom', zorder=5,
                fontsize=12, color=C_TEXT, alpha=0.50)

    # ── Grid ──────────────────────────────────────────────────────────────────
    for frac in [0.25, 0.5, 0.75, 1.0]:
        gx = BAR_L + frac * BAR_W
        ax.plot([gx, gx], [PLOT_BOT, PLOT_TOP], color=C_GRID, lw=1,
                linestyle='--', zorder=2, alpha=0.8)

    # ── Bars ──────────────────────────────────────────────────────────────────
    n        = len(positions)
    row_h    = (PLOT_TOP - PLOT_BOT) / n
    bar_h    = min(32, row_h * 0.60)
    max_oi   = positions[0]['oi']
    total_oi = sum(p['oi'] for p in positions)

    for i, pos in enumerate(positions):
        y_c     = PLOT_TOP - (i + 0.5) * row_h
        scale   = pos['oi'] / max_oi
        long_w  = (pos['long']  / pos['oi']) * scale * BAR_W if pos['oi'] else 0
        short_w = (pos['short'] / pos['oi']) * scale * BAR_W if pos['oi'] else 0

        ax.barh(y_c, long_w,  height=bar_h, left=BAR_L,            color=C_LONG,  zorder=3, linewidth=0)
        ax.barh(y_c, short_w, height=bar_h, left=BAR_L + long_w,   color=C_SHORT, zorder=3, linewidth=0)

        # Token label — PF Spekk VAR (pure alpha tokens like SUI, BTC, ETH)
        ax.text(LABEL_X, y_c, pos['token'],
                ha='right', va='center', zorder=5,
                fontproperties=fp_brand(15, 'black'), color=C_TEXT)

        # OI value + share — system font (has $ and %)
        pct = pos['oi'] / total_oi * 100
        ax.text(VALUE_X, y_c, f"{fmt_k(pos['oi'])}   ({pct:.1f}%)",
                ha='left', va='center', zorder=5,
                fontsize=14, color=C_TEXT)

        # L/S ratio — show number only, or NetLong/NetShort
        ls_raw = pos['ls']
        try:
            ls_val = float(ls_raw)
            ls_str = f'{ls_val:.2f}' if ls_val < 100 else f'{ls_val:.0f}'
        except (ValueError, TypeError):
            ls_str = str(ls_raw)   # "NetShort" / "NetLong"
        ax.text(LS_X, y_c, ls_str,
                ha='right', va='center', zorder=5,
                fontsize=13, color=C_TEXT, alpha=0.65)

    # ── Legend — system font ──────────────────────────────────────────────────
    LEG_Y = LEG_Y_VAL
    for offset, color, label in [(0, C_LONG, 'Long'), (74, C_SHORT, 'Short')]:
        ax.add_patch(mpatches.FancyBboxPatch(
            (BAR_L + offset, LEG_Y - 7), 14, 14,
            boxstyle='square,pad=0', color=color, zorder=5))
        ax.text(BAR_L + offset + 20, LEG_Y, label,
                va='center', zorder=5, fontsize=13, color=C_TEXT)

    # ── Key Stats — system font ───────────────────────────────────────────────
    total_long  = sum(p['long']  for p in positions)
    total_short = sum(p['short'] for p in positions)
    overall_ls  = total_long / total_short if total_short > 0 else 0
    top_token   = positions[0]['token']
    top_pct     = positions[0]['oi'] / total_oi * 100

    stats = '    ·    '.join([
        f'Total OI: {fmt_k(total_oi)}',
        f'Largest: {top_token} ({top_pct:.1f}%)',
        f'Overall L/S: {overall_ls:.3f}',
        f'Long: {fmt_k(total_long)}    Short: {fmt_k(total_short)}',
    ])
    ax.text(W / 2, STATS_Y, stats,
            ha='center', va='bottom', zorder=5,
            fontsize=16, fontweight='semibold', color=C_TEXT)

    # ── Source — system font ──────────────────────────────────────────────────
    ax.text(W / 2, SOURCE_Y, 'Source: Typus Protocol  /  Sentio Platform',
            ha='center', va='bottom', zorder=5,
            fontsize=13, color=C_TEXT, alpha=0.45)

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=DPI, facecolor=C_BG,
                bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f'✅ OI Distribution → {output_path}')


# ─── Chart: 7-Day Vertical Bar (shared helper) ───────────────────────────────
def _chart_7day_bars(rows, title, value_fmt, output_path,
                     color_pos=None, color_neg=None, single_color=None,
                     stat_lines=None):
    """
    Vertical bar chart for 7-day (Mon–Sun) data.

    rows        — list of {day, date, value}
    title       — chart title (pure alphabetic → brand font)
    value_fmt   — callable: float → label string
    color_pos   — bar color for positive values (or None)
    color_neg   — bar color for negative values
    single_color— use one color for all bars (ignores pos/neg)
    stat_lines  — list of strings for the bottom stats line
    """
    if not rows:
        print(f'⚠️  No data — skipping {title} chart')
        return

    values = [r['value'] if isinstance(r['value'], (int, float)) else 0 for r in rows]
    days   = [r['day'] for r in rows]

    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=C_BG)
    ax  = fig.add_axes([0, 0, 1, 1], facecolor=C_BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')

    add_watermark(ax, alpha=0.08)

    # ── Layout ────────────────────────────────────────────────────────────────
    TITLE_Y  = H - 58
    PLOT_TOP = TITLE_Y - 52
    PLOT_BOT = 120
    STATS_Y  = 52
    SOURCE_Y = 20
    BAR_L    = 100
    BAR_R    = W - 80
    BAR_AREA = BAR_R - BAR_L

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.text(W / 2, TITLE_Y, title,
            ha='center', va='bottom', zorder=5,
            fontproperties=fp_brand(34, 'black'), color=C_TEXT)

    # ── Grid lines ────────────────────────────────────────────────────────────
    plot_h = PLOT_TOP - PLOT_BOT
    v_max  = max(abs(v) for v in values) if values else 1
    has_neg = any(v < 0 for v in values)

    if has_neg:
        # zero line in the middle-ish; scale symmetrically
        scale  = v_max
        zero_y = PLOT_BOT + plot_h / 2
        pos_h  = plot_h / 2
        neg_h  = plot_h / 2
    else:
        scale  = v_max
        zero_y = PLOT_BOT
        pos_h  = plot_h
        neg_h  = 0

    # horizontal grid at 25%, 50%, 75%, 100% of positive axis
    for frac in [0.25, 0.5, 0.75, 1.0]:
        gy = zero_y + frac * pos_h
        ax.plot([BAR_L, BAR_R], [gy, gy], color=C_GRID, lw=1,
                linestyle='--', zorder=2, alpha=0.8)
        if has_neg:
            gy2 = zero_y - frac * neg_h
            ax.plot([BAR_L, BAR_R], [gy2, gy2], color=C_GRID, lw=1,
                    linestyle='--', zorder=2, alpha=0.6)

    # zero line
    ax.plot([BAR_L, BAR_R], [zero_y, zero_y], color=C_TEXT, lw=1.2,
            zorder=3, alpha=0.25)

    # ── Bars ──────────────────────────────────────────────────────────────────
    n       = len(rows)
    slot_w  = BAR_AREA / n
    bar_w   = slot_w * 0.55

    for i, (val, day) in enumerate(zip(values, days)):
        x_c = BAR_L + (i + 0.5) * slot_w

        if single_color:
            color = single_color
        else:
            color = color_pos if val >= 0 else color_neg

        if scale == 0:
            bar_h_px = 0
        else:
            bar_h_px = abs(val) / scale * (pos_h if val >= 0 else neg_h)

        y_bot = zero_y if val >= 0 else zero_y - bar_h_px
        ax.bar(x_c, bar_h_px, width=bar_w, bottom=y_bot,
               color=color, zorder=4, linewidth=0)

        # value label: always above the bar (positive → above top, negative → above zero line)
        label = value_fmt(val)
        if val >= 0:
            lbl_y = y_bot + bar_h_px + 6
        else:
            lbl_y = zero_y + 6   # just above zero line, so it doesn't clash with day label
        ax.text(x_c, lbl_y, label,
                ha='center', va='bottom', zorder=5,
                fontsize=12, color=C_TEXT)

        # date label below plot (MM/DD format)
        date_str = rows[i].get('date', day)
        if len(date_str) == 10:   # 'YYYY-MM-DD'
            date_label = date_str[5:].replace('-', '/')   # 'MM/DD'
        else:
            date_label = date_str
        ax.text(x_c, PLOT_BOT - 12, date_label,
                ha='center', va='top', zorder=5,
                fontsize=13, color=C_TEXT, alpha=0.65)

    # ── Stats ─────────────────────────────────────────────────────────────────
    if stat_lines:
        stats_str = '    ·    '.join(stat_lines)
        ax.text(W / 2, STATS_Y, stats_str,
                ha='center', va='bottom', zorder=5,
                fontsize=16, fontweight='semibold', color=C_TEXT)

    # ── Source ────────────────────────────────────────────────────────────────
    ax.text(W / 2, SOURCE_Y, 'Source: Typus Protocol  /  Sentio Platform',
            ha='center', va='bottom', zorder=5,
            fontsize=13, color=C_TEXT, alpha=0.45)

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=DPI, facecolor=C_BG,
                bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f'✅ {title} → {output_path}')


# ─── Chart: Daily PnL ─────────────────────────────────────────────────────────
def chart_daily_pnl(data, output_path):
    rows = data.get('daily_pnl', [])
    if not rows:
        print('⚠️  No P&L data — skipping Daily PnL chart')
        return
    values = [r['value'] if isinstance(r['value'], (int, float)) else 0 for r in rows]
    total  = sum(values)
    wins   = sum(1 for v in values if v > 0)
    _chart_7day_bars(
        rows, title='Daily Trader PnL',
        value_fmt=fmt_k,
        output_path=output_path,
        color_pos=C_LONG, color_neg=C_SHORT,
        stat_lines=[
            f'Weekly Total: {fmt_k(total)}',
            f'Profitable Days: {wins}/7',
            f'Best: {fmt_k(max(values))}',
            f'Worst: {fmt_k(min(values))}',
        ]
    )


# ─── Chart: Daily Liquidation ─────────────────────────────────────────────────
def chart_daily_liquidation(data, output_path):
    rows = data.get('daily_liquidation', [])
    if not rows:
        print('⚠️  No liquidation data — skipping Daily Liquidation chart')
        return
    values = [r['value'] if isinstance(r['value'], (int, float)) else 0 for r in rows]
    total  = sum(values)
    peak   = max(values)
    _chart_7day_bars(
        rows, title='Daily Liquidation',
        value_fmt=fmt_k,
        output_path=output_path,
        single_color=C_SHORT,
        stat_lines=[
            f'Weekly Total: {fmt_k(total)}',
            f'Peak Day: {fmt_k(peak)}',
            f'Avg Daily: {fmt_k(total / len(values))}',
        ]
    )


# ─── Chart: Daily Active Users ────────────────────────────────────────────────
def chart_dau(data, output_path):
    rows = data.get('daily_dau', [])
    if not rows:
        print('⚠️  No DAU data — skipping DAU chart')
        return
    values = [r['value'] if isinstance(r['value'], (int, float)) else 0 for r in rows]
    total  = sum(values)
    peak   = max(values)

    def fmt_int(v):
        return str(int(v))

    _chart_7day_bars(
        rows, title='Daily Active Users',
        value_fmt=fmt_int,
        output_path=output_path,
        single_color=C_LONG,
        stat_lines=[
            f'Weekly Total: {total}',
            f'Peak: {peak}',
            f'Avg Daily: {total / len(values):.1f}',
        ]
    )


# ─── Chart: Daily Volume ──────────────────────────────────────────────────────
def chart_daily_volume(data, output_path):
    rows = data.get('daily_volume', [])
    if not rows:
        print('⚠️  No daily volume data — skipping Daily Volume chart')
        return
    values = [r['value'] if isinstance(r['value'], (int, float)) else 0 for r in rows]
    total  = sum(values)
    peak   = max(values)
    _chart_7day_bars(
        rows, title='Daily Trading Volume',
        value_fmt=fmt_k,
        output_path=output_path,
        single_color=C_LONG,
        stat_lines=[
            f'Weekly Total: {fmt_k(total)}',
            f'Peak Day: {fmt_k(peak)}',
            f'Avg Daily: {fmt_k(total / len(values))}',
        ]
    )


# ─── Chart: OI History ────────────────────────────────────────────────────────
def chart_oi_history(data, output_path):
    """
    Multi-line chart: daily OI by token (top 5 from Section 8 positions).
    X-axis = 7 days (Mon–Sun), one line per top-5 token + Total.
    """
    oi_daily  = data.get('oi_daily', [])
    positions = data.get('positions', [])

    if not oi_daily:
        print('⚠️  No OI history snapshot data — skipping OI History chart')
        return

    # Top-5 tokens from Section 8 (by OI), fallback to oi_tokens minus 'Total'
    if positions:
        top5 = [p['token'] for p in positions[:5]]
    else:
        tokens_all = [t for t in data.get('oi_tokens', []) if t != 'Total']
        top5 = tokens_all[:5]

    # Collect dates and per-token series
    dates  = [row['date'] for row in oi_daily]      # e.g. ['2026-02-02', ...]
    labels = [d[5:]  for d in dates]                # 'MM-DD'

    # Build series: {token: [val, val, ...]}
    # Only include tokens that have at least one non-zero value in the snapshot
    series = {}
    for tok in top5:
        vals = [row['token_values'].get(tok, 0.0) for row in oi_daily]
        if any(v > 0 for v in vals):
            series[tok] = vals

    if not series:
        print('⚠️  No token OI data found in daily snapshot — skipping OI History chart')
        plt.close(fig)
        return

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=C_BG)
    ax  = fig.add_axes([0, 0, 1, 1], facecolor=C_BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')

    add_watermark(ax, alpha=0.06)

    # ── Layout ────────────────────────────────────────────────────────────────
    TITLE_Y  = H - 58
    PLOT_TOP = TITLE_Y - 52
    PLOT_BOT = 120
    STATS_Y  = 52
    SOURCE_Y = 20
    LINE_L   = 100
    LINE_R   = W - 140   # leave room for legend on right
    LINE_W   = LINE_R - LINE_L
    n_pts    = len(dates)

    # ── Title ─────────────────────────────────────────────────────────────────
    ax.text(W / 2, TITLE_Y, 'OI History',
            ha='center', va='bottom', zorder=5,
            fontproperties=fp_brand(34, 'black'), color=C_TEXT)

    # ── Y scale ───────────────────────────────────────────────────────────────
    all_vals = [v for tok_vals in series.values() for v in tok_vals]
    y_max    = max(all_vals) if all_vals else 1
    y_min    = 0
    y_range  = y_max - y_min or 1
    plot_h   = PLOT_TOP - PLOT_BOT

    def to_px(v):
        return PLOT_BOT + (v - y_min) / y_range * plot_h

    # ── Grid lines ────────────────────────────────────────────────────────────
    for frac in [0.25, 0.5, 0.75, 1.0]:
        gy = PLOT_BOT + frac * plot_h
        ax.plot([LINE_L, LINE_R], [gy, gy], color=C_GRID, lw=1,
                linestyle='--', zorder=2, alpha=0.8)
        label_v = y_min + frac * y_range
        ax.text(LINE_L - 6, gy, fmt_k(label_v),
                ha='right', va='center', zorder=5,
                fontsize=11, color=C_TEXT, alpha=0.55)

    # ── X positions ───────────────────────────────────────────────────────────
    if n_pts > 1:
        x_positions = [LINE_L + i / (n_pts - 1) * LINE_W for i in range(n_pts)]
    else:
        x_positions = [LINE_L + LINE_W / 2]

    # ── Day labels ────────────────────────────────────────────────────────────
    for i, xp in enumerate(x_positions):
        raw = dates[i] if i < len(dates) else ''
        date_label = raw[5:].replace('-', '/') if len(raw) == 10 else raw  # 'MM/DD'
        ax.text(xp, PLOT_BOT - 12, date_label,
                ha='center', va='top', zorder=5,
                fontsize=13, color=C_TEXT, alpha=0.65)

    # ── Line colors ───────────────────────────────────────────────────────────
    LINE_COLORS = [
        '#5056EA', '#E8556D', '#F4A261', '#2A9D8F', '#E9C46A',
        '#264653', '#A8DADC',
    ]

    # ── Draw lines + dots ─────────────────────────────────────────────────────
    legend_items = []
    for idx, tok in enumerate(series.keys()):
        color  = LINE_COLORS[idx % len(LINE_COLORS)]
        vals   = series[tok]
        pts_x  = x_positions[:len(vals)]
        pts_y  = [to_px(v) for v in vals]

        # Line
        ax.plot(pts_x, pts_y, color=color, lw=2.5, zorder=4, solid_capstyle='round')
        # Dots
        for px_, py_ in zip(pts_x, pts_y):
            ax.scatter([px_], [py_], color=color, s=40, zorder=5, linewidths=0)

        legend_items.append((color, tok))

    # ── Legend (right side, vertical) ─────────────────────────────────────────
    LEG_X    = LINE_R + 20
    LEG_Y_TOP = PLOT_TOP
    row_gap   = (PLOT_TOP - PLOT_BOT) / (len(legend_items) + 1)
    for i, (color, tok) in enumerate(legend_items):
        ly = LEG_Y_TOP - (i + 0.5) * row_gap
        ax.plot([LEG_X, LEG_X + 22], [ly, ly], color=color, lw=2.5, zorder=5)
        ax.text(LEG_X + 28, ly, tok,
                ha='left', va='center', zorder=5,
                fontproperties=fp_brand(13, 'semibold'), color=C_TEXT)

    # ── Stats ─────────────────────────────────────────────────────────────────
    if oi_daily:
        start_total = oi_daily[0]['token_values'].get('Total', 0)
        end_total   = oi_daily[-1]['token_values'].get('Total', 0)
        chg_pct     = (end_total - start_total) / start_total * 100 if start_total else 0
        sign        = '+' if chg_pct >= 0 else ''
        stats_str   = '   |   '.join([
            f'Week Start: {fmt_k(start_total)}',
            f'Week End: {fmt_k(end_total)}',
            f'Change: {sign}{chg_pct:.1f}%',
        ])
        ax.text(W / 2, STATS_Y, stats_str,
                ha='center', va='bottom', zorder=5,
                fontsize=16, fontweight='semibold', color=C_TEXT)

    # ── Source ────────────────────────────────────────────────────────────────
    ax.text(W / 2, SOURCE_Y, 'Source: Typus Protocol  /  Sentio Platform',
            ha='center', va='bottom', zorder=5,
            fontsize=13, color=C_TEXT, alpha=0.45)

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=DPI, facecolor=C_BG,
                bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f'✅ OI History → {output_path}')


# ─── Chart: TLP Price ─────────────────────────────────────────────────────────
def chart_tlp_price(data, output_path):
    """
    Dual-line chart: mTLP and iTLP-TYPUS daily close price over 7 days.
    mTLP = blue (C_LONG), iTLP-TYPUS = orange.
    """
    rows = data.get('tlp_daily', [])
    if not rows:
        print('⚠️  No TLP daily price data (Section 1 Daily Snapshot) — skipping TLP Price chart')
        return

    dates  = [r['date'] for r in rows]
    labels = [d[5:] if len(d) == 10 else d for d in dates]
    mtlp_vals = [r['mtlp'] for r in rows]
    itlp_vals = [r['itlp'] for r in rows]
    n_pts = len(rows)

    C_ORANGE = '#F4A261'

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=C_BG)
    ax  = fig.add_axes([0, 0, 1, 1], facecolor=C_BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')
    add_watermark(ax, alpha=0.06)

    # ── Layout ────────────────────────────────────────────────────────────────
    TITLE_Y  = H - 58
    PLOT_TOP = TITLE_Y - 52
    PLOT_BOT = 120
    STATS_Y  = 52
    SOURCE_Y = 20
    LINE_L   = 100
    LINE_R   = W - 140
    LINE_W   = LINE_R - LINE_L

    ax.text(W / 2, TITLE_Y, 'TLP Price',
            ha='center', va='bottom', zorder=5,
            fontproperties=fp_brand(34, 'black'), color=C_TEXT)

    # ── Y scale (shared axis, but compute range sensibly) ─────────────────────
    all_vals = [v for v in mtlp_vals + itlp_vals if v is not None]
    if not all_vals:
        print('⚠️  TLP daily price all None — skipping chart')
        plt.close(fig)
        return
    y_min = min(all_vals) * 0.998
    y_max = max(all_vals) * 1.002
    y_range = y_max - y_min or 0.001
    plot_h  = PLOT_TOP - PLOT_BOT

    def to_px(v):
        return PLOT_BOT + (v - y_min) / y_range * plot_h

    # ── Grid lines ─────────────────────────────────────────────────────────────
    for frac in [0.25, 0.5, 0.75, 1.0]:
        gy = PLOT_BOT + frac * plot_h
        ax.plot([LINE_L, LINE_R], [gy, gy], color=C_GRID, lw=1,
                linestyle='--', zorder=2, alpha=0.8)
        lv = y_min + frac * y_range
        ax.text(LINE_L - 6, gy, f'${lv:.4f}',
                ha='right', va='center', zorder=5,
                fontsize=11, color=C_TEXT, alpha=0.55)

    # ── X positions ────────────────────────────────────────────────────────────
    if n_pts > 1:
        x_pos = [LINE_L + i / (n_pts - 1) * LINE_W for i in range(n_pts)]
    else:
        x_pos = [LINE_L + LINE_W / 2]

    # ── Day labels (only Mondays for multi-week view) ──────────────────────────
    for i, xp in enumerate(x_pos):
        if n_pts > 7 and rows[i].get('day') != 'Mon':
            continue
        lbl = labels[i].replace('-', '/') if '-' in labels[i] else labels[i]
        ax.text(xp, PLOT_BOT - 12, lbl,
                ha='center', va='top', zorder=5,
                fontsize=13, color=C_TEXT, alpha=0.65)

    # ── Lines ─────────────────────────────────────────────────────────────────
    def draw_line(vals, color, label):
        valid_x = [x_pos[i] for i, v in enumerate(vals) if v is not None]
        valid_y = [to_px(v) for v in vals if v is not None]
        if len(valid_x) < 2:
            return
        ax.plot(valid_x, valid_y, color=color, lw=2.5, zorder=4, solid_capstyle='round')
        for px_, py_ in zip(valid_x, valid_y):
            ax.scatter([px_], [py_], color=color, s=40, zorder=5, linewidths=0)

    draw_line(mtlp_vals, C_LONG, 'mTLP')
    draw_line(itlp_vals, C_ORANGE, 'iTLP-TYPUS')

    # ── Legend (right side) ────────────────────────────────────────────────────
    LEG_X = LINE_R + 20
    for i, (color, lbl) in enumerate([(C_LONG, 'mTLP'), (C_ORANGE, 'iTLP-TYPUS')]):
        ly = PLOT_TOP - (i + 1) * (PLOT_TOP - PLOT_BOT) / 3
        ax.plot([LEG_X, LEG_X + 22], [ly, ly], color=color, lw=2.5, zorder=5)
        ax.text(LEG_X + 28, ly, lbl,
                ha='left', va='center', zorder=5,
                fontproperties=fp_brand(13, 'semibold'), color=C_TEXT)

    # ── Stats (always use current week = last 7 rows) ──────────────────────────
    curr = rows[-7:] if len(rows) >= 7 else rows
    m_start = curr[0].get('mtlp')  if curr else None
    m_end   = curr[-1].get('mtlp') if curr else None
    i_start = curr[0].get('itlp')  if curr else None
    i_end   = curr[-1].get('itlp') if curr else None
    parts = []
    if m_start and m_end:
        chg = (m_end - m_start) / m_start * 100
        sign = '+' if chg >= 0 else ''
        parts.append(f'mTLP: ${m_start:.4f} → ${m_end:.4f} ({sign}{chg:.2f}%)')
    if i_start and i_end:
        chg = (i_end - i_start) / i_start * 100
        sign = '+' if chg >= 0 else ''
        parts.append(f'iTLP: ${i_start:.4f} → ${i_end:.4f} ({sign}{chg:.2f}%)')
    if parts:
        ax.text(W / 2, STATS_Y, '   |   '.join(parts),
                ha='center', va='bottom', zorder=5,
                fontsize=16, fontweight='semibold', color=C_TEXT)

    ax.text(W / 2, SOURCE_Y, 'Source: Typus Protocol  /  Sentio Platform',
            ha='center', va='bottom', zorder=5,
            fontsize=13, color=C_TEXT, alpha=0.45)

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=DPI, facecolor=C_BG, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f'✅ TLP Price → {output_path}')


# ─── Chart: Fee Breakdown ──────────────────────────────────────────────────────
def chart_fee_breakdown(data, output_path):
    """
    Stacked bar chart: daily TLP Fee + Protocol Fee over 7 days.
    TLP Fee = blue (C_LONG), Protocol Fee = coral (C_SHORT).
    """
    tlp_rows  = data.get('daily_tlp_fee', [])
    prot_rows = data.get('daily_protocol_fee', [])

    if not tlp_rows:
        print('⚠️  No daily fee data (Section 13) — skipping Fee Breakdown chart')
        return

    # Build aligned daily arrays
    days    = [r['day']  for r in tlp_rows]
    dates   = [r['date'] for r in tlp_rows]
    tlp_v   = [float(r['value']) if isinstance(r['value'], float) else 0.0 for r in tlp_rows]

    # Protocol fee rows indexed by day
    prot_map = {r['day']: (float(r['value']) if isinstance(r['value'], float) else 0.0)
                for r in prot_rows}
    prot_v   = [prot_map.get(d, 0.0) for d in days]

    totals = [t + p for t, p in zip(tlp_v, prot_v)]
    n = len(days)

    # ── Figure ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=C_BG)
    ax  = fig.add_axes([0, 0, 1, 1], facecolor=C_BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')
    add_watermark(ax, alpha=0.08)

    TITLE_Y  = H - 58
    PLOT_TOP = TITLE_Y - 82   # extra 30px above bars for legend
    PLOT_BOT = 120
    STATS_Y  = 52
    SOURCE_Y = 20
    BAR_L    = 120
    BAR_R    = W - 80
    BAR_AREA = BAR_R - BAR_L

    ax.text(W / 2, TITLE_Y, 'Fee Breakdown',
            ha='center', va='bottom', zorder=5,
            fontproperties=fp_brand(34, 'black'), color=C_TEXT)

    # ── Y scale ───────────────────────────────────────────────────────────────
    y_max   = max(totals) if totals else 1
    y_range = y_max * 1.15 or 1
    plot_h  = PLOT_TOP - PLOT_BOT

    def to_px_h(v):
        return v / y_range * plot_h

    # ── Grid ──────────────────────────────────────────────────────────────────
    for frac in [0.25, 0.5, 0.75, 1.0]:
        gy = PLOT_BOT + frac * plot_h
        ax.plot([BAR_L, BAR_R], [gy, gy], color=C_GRID, lw=1,
                linestyle='--', zorder=2, alpha=0.8)
        lv = frac * y_range
        ax.text(BAR_L - 6, gy, f'${lv:.0f}',
                ha='right', va='center', zorder=5,
                fontsize=11, color=C_TEXT, alpha=0.55)

    # ── Bars ──────────────────────────────────────────────────────────────────
    bar_w   = BAR_AREA / n * 0.55
    spacing = BAR_AREA / n

    for i in range(n):
        cx = BAR_L + i * spacing + spacing / 2
        bx = cx - bar_w / 2

        ph = to_px_h(prot_v[i])
        th = to_px_h(tlp_v[i])

        # Protocol Fee (bottom, coral)
        if prot_v[i] > 0:
            rect_p = plt.Rectangle((bx, PLOT_BOT), bar_w, ph,
                                    color=C_SHORT, zorder=3)
            ax.add_patch(rect_p)

        # TLP Fee (top, blue)
        if tlp_v[i] > 0:
            rect_t = plt.Rectangle((bx, PLOT_BOT + ph), bar_w, th,
                                    color=C_LONG, zorder=3)
            ax.add_patch(rect_t)

        # Total label above bar
        total_h = to_px_h(totals[i])
        ax.text(cx, PLOT_BOT + total_h + 8, f'${totals[i]:.0f}',
                ha='center', va='bottom', zorder=5,
                fontsize=11, color=C_TEXT)

        # Day label
        ax.text(cx, PLOT_BOT - 12, days[i],
                ha='center', va='top', zorder=5,
                fontsize=13, color=C_TEXT, alpha=0.65)

    # ── Legend (above bars, between title and plot area) ─────────────────────
    LEG_Y = PLOT_TOP + 16   # sits in the gap between PLOT_TOP and title text
    for xi, (color, lbl) in enumerate([(C_LONG, 'TLP Fee'), (C_SHORT, 'Protocol Fee')]):
        lx = W / 2 - 160 + xi * 240
        ax.add_patch(plt.Rectangle((lx, LEG_Y - 8), 16, 16, color=color, zorder=5))
        ax.text(lx + 22, LEG_Y, lbl,
                ha='left', va='center', zorder=5,
                fontsize=14, color=C_TEXT)

    # ── Stats ──────────────────────────────────────────────────────────────────
    total_tlp  = sum(tlp_v)
    total_prot = sum(prot_v)
    total_all  = total_tlp + total_prot
    peak_day   = days[totals.index(max(totals))] if totals else '—'
    stats_str  = '   |   '.join([
        f'Weekly TLP Fee: ${total_tlp:.2f}',
        f'Protocol Fee: ${total_prot:.2f}',
        f'Total: ${total_all:.2f}',
        f'Peak: {peak_day}',
    ])
    ax.text(W / 2, STATS_Y, stats_str,
            ha='center', va='bottom', zorder=5,
            fontsize=15, fontweight='semibold', color=C_TEXT)

    ax.text(W / 2, SOURCE_Y, 'Source: Typus Protocol  /  Sentio Platform',
            ha='center', va='bottom', zorder=5,
            fontsize=13, color=C_TEXT, alpha=0.45)

    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=DPI, facecolor=C_BG, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    print(f'✅ Fee Breakdown → {output_path}')


# ─── Helpers ──────────────────────────────────────────────────────────────────
def load_prev_tlp_daily(current_file, n_back=3):
    """Return tlp_daily rows from the n_back sentio files preceding current_file (sorted by mtime)."""
    all_files = sorted(
        [f for f in glob.glob(os.path.join(SENTIO_DIR, 'week-*.md'))
         if '-brief' not in os.path.basename(f)],
        key=os.path.getmtime
    )
    abs_current = os.path.abspath(current_file)
    try:
        idx = [os.path.abspath(f) for f in all_files].index(abs_current)
    except ValueError:
        idx = len(all_files)
    prev_files = all_files[max(0, idx - n_back):idx]
    rows = []
    for pf in prev_files:
        d = parse_sentio(pf)
        rows.extend(d.get('tlp_daily', []))
    return rows


def fetch_tlp_history_from_api(exclude_dates=None, n_extra_weeks=3):
    """Fetch ~n_extra_weeks of mTLP/iTLP daily prices from Sentio API as fallback."""
    import urllib.request, json as _json
    from datetime import datetime, timezone
    import time as _time

    api_key_path = os.path.join(SCRIPT_DIR, '..', 'fetch-sentio-data', '.api-key')
    api_key_path = os.path.abspath(api_key_path)
    if not os.path.exists(api_key_path):
        return []
    with open(api_key_path) as f:
        api_key = f.read().strip()
    if not api_key:
        return []

    end_ts   = (_time.time() // 86400) * 86400   # start of today UTC
    start_ts = int(end_ts - (n_extra_weeks * 7 + 1) * 86400)
    end_ts   = int(end_ts)

    payload = {
        "version": 9,
        "timeRange": {"start": str(start_ts), "end": str(end_ts),
                      "step": 86400, "timezone": "UTC"},
        "limit": 20,
        "queries": [
            {"metricsQuery": {"query": "tlp_price", "alias": "mTLP", "id": "a",
                              "labelSelector": {"index": "0"}, "aggregate": None,
                              "functions": [], "color": "", "disabled": False},
             "dataSource": "METRICS", "sourceName": ""},
            {"metricsQuery": {"query": "tlp_price", "alias": "iTLP-TYPUS", "id": "b",
                              "labelSelector": {"index": "1"}, "aggregate": None,
                              "functions": [], "color": "", "disabled": False},
             "dataSource": "METRICS", "sourceName": ""}
        ],
        "formulas": [],
        "cachePolicy": {"noCache": False, "cacheTtlSecs": 43200, "cacheRefreshTtlSecs": 1800}
    }

    try:
        req = urllib.request.Request(
            "https://api.sentio.xyz/v1/insights/typus/typus_perp/query",
            _json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'api-key': api_key,
                     'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = _json.loads(r.read())

        mtlp_vals = result['results'][0]['matrix']['samples'][0]['values']
        itlp_vals = result['results'][1]['matrix']['samples'][0]['values']

        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        skip = set(exclude_dates or [])
        rows = []
        for mv, iv in zip(mtlp_vals, itlp_vals):
            dt = datetime.fromtimestamp(int(mv['timestamp']), tz=timezone.utc)
            date_str = dt.strftime('%Y-%m-%d')
            if date_str in skip:
                continue
            rows.append({
                'day':  day_names[dt.weekday()],
                'date': date_str,
                'mtlp': float(mv['value']),
                'itlp': float(iv['value']),
            })
        return rows
    except Exception as e:
        print(f'⚠️  TLP history API fetch failed: {e}')
        return []


# ─── Main ─────────────────────────────────────────────────────────────────────
def find_latest_sentio():
    files = [f for f in glob.glob(os.path.join(SENTIO_DIR, 'week-*.md'))
             if '-brief' not in os.path.basename(f)]
    return max(files, key=os.path.getmtime) if files else None


def main():
    parser = argparse.ArgumentParser(description='Typus Weekly Chart Generator')
    parser.add_argument('--file',  help='Path to sentio-data MD file')
    parser.add_argument('--chart', default='all',
                        choices=['all', 'oi-dist', 'pnl', 'liquidation', 'dau',
                                 'volume', 'oi-history', 'tlp-price', 'fee-breakdown'],
                        help='Chart type (default: all)')
    args = parser.parse_args()

    sentio_file = args.file or find_latest_sentio()
    if not sentio_file:
        print('❌ No sentio-data file found. Run /fetch-sentio-data first.')
        sys.exit(1)

    print(f'📂 Reading: {os.path.basename(sentio_file)}')
    data     = parse_sentio(sentio_file)
    basename = os.path.splitext(os.path.basename(sentio_file))[0]

    if args.chart in ('all', 'oi-dist'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-oi-distribution.png')
        chart_oi_distribution(data, out)

    if args.chart in ('all', 'pnl'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-daily-pnl.png')
        chart_daily_pnl(data, out)

    if args.chart in ('all', 'liquidation'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-daily-liquidation.png')
        chart_daily_liquidation(data, out)

    if args.chart in ('all', 'dau'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-daily-dau.png')
        chart_dau(data, out)

    if args.chart in ('all', 'volume'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-daily-volume.png')
        chart_daily_volume(data, out)

    if args.chart in ('all', 'oi-history'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-oi-history.png')
        chart_oi_history(data, out)

    if args.chart in ('all', 'tlp-price'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-tlp-price.png')
        # Extend to ~4-week view by prepending previous 3 weeks' daily prices
        data_4w = dict(data)
        history = load_prev_tlp_daily(os.path.abspath(sentio_file), n_back=3)
        if not history:
            curr_dates = {r['date'] for r in data.get('tlp_daily', [])}
            history = fetch_tlp_history_from_api(exclude_dates=curr_dates, n_extra_weeks=3)
            # Remove API data from or after the current week start to avoid ordering issues
            if curr_dates and history:
                min_curr = min(curr_dates)
                history = [r for r in history if r.get('date', '9999') < min_curr]
        data_4w['tlp_daily'] = history + data.get('tlp_daily', [])
        chart_tlp_price(data_4w, out)

    if args.chart in ('all', 'fee-breakdown'):
        out = os.path.join(OUTPUTS_DIR, f'{basename}-fee-breakdown.png')
        chart_fee_breakdown(data, out)


if __name__ == '__main__':
    main()
