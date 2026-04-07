---
name: generate-charts
description: Generate brand-consistent data charts (PNG) for Typus weekly reports from sentio-data files.
user-invocable: true
allowed-tools: Read, Glob, Bash, Write
---

# Typus 週報圖表生成工具

從 sentio-data MD 文件讀取數據，產出符合 Typus 品牌風格的圖表 PNG，供 `/publish-medium` 自動上傳至 Medium 草稿。

---

## 執行流程

### 第一步：確認 sentio-data 文件存在

```bash
ls -t data-sources/sentio-data/week-*[0-9].md 2>/dev/null | head -3
```

若無結果，提示用戶先執行 `/fetch-sentio-data`。

### 第二步：執行圖表生成腳本

```bash
python3 .claude/skills/generate-charts/generate_charts.py [--file PATH] [--chart CHART_TYPE]
```

**參數說明**：
- `--file PATH`：指定 sentio-data MD 文件（省略則自動使用最新文件）
- `--chart TYPE`：只生成指定圖表（省略則生成所有圖表）

**支援的圖表**：

| 參數 | 標題 | 輸出檔案後綴 | 數據來源 |
|------|------|-------------|---------|
| `oi-dist` | OI Distribution | `-oi-distribution.png` | Section 8 Opening Positions |
| `pnl` | Daily Trader PnL | `-daily-pnl.png` | Section 5 Daily P&L |
| `liquidation` | Daily Liquidation | `-daily-liquidation.png` | Section 6 Daily Liquidation |
| `dau` | Daily Active Users | `-daily-dau.png` | Section 7 Daily DAU |
| `volume` | Daily Trading Volume | `-daily-volume.png` | Section 12 Daily Total Volume |
| `oi-history` | OI History | `-oi-history.png` | Section 10 Daily OI Snapshot |
| `tlp-price` | TLP Price | `-tlp-price.png` | Section 1 Daily Price Snapshot |
| `fee-breakdown` | Fee Breakdown | `-fee-breakdown.png` | Section 13 Daily Fees |

### 第三步：顯示輸出路徑

所有圖表輸出至：
```
outputs/weekly/final/{week-basename}-{suffix}.png
```

例：`outputs/weekly/final/week-4-february-2026-oi-distribution.png`

---

## 圖表設計規格

- **尺寸**：1400×640 px（@100 DPI）
- **背景**：白色 #FFFFFF
- **主色**：Typus 品牌藍 #5056EA（Long / 正值）/ 珊瑚紅 #E8556D（Short / 負值）
- **字型**：標題 + 幣種名稱使用 PF Spekk VAR Black；數據文字使用系統 Helvetica
- **Watermark**：TYPUS 文字浮水印（opacity 0.08）；如已安裝 cairosvg，使用 SVG logo

---

## 各圖說明

### OI Distribution（`oi-dist`）
- 水平堆疊長條圖，OI 前 5 大幣種
- 藍色 = Long，紅色 = Short
- 右側：OI 金額 + 總佔比 + L/S Ratio
- 底部 stats：Total OI / 最大幣種 / Overall L/S / Long & Short 分開金額

### Daily Trader PnL（`pnl`）
- 垂直長條圖，7 天（Mon–Sun）
- 正值 = 藍色，負值 = 紅色
- 底部 stats：Weekly Total / Profitable Days / Best / Worst

### Daily Liquidation（`liquidation`）
- 垂直長條圖，7 天，全紅色
- 底部 stats：Weekly Total / Peak Day / Avg Daily

### Daily Active Users（`dau`）
- 垂直長條圖，7 天，全藍色
- 底部 stats：Weekly Total / Peak / Avg Daily

### Daily Trading Volume（`volume`）
- 垂直長條圖，7 天，全藍色
- 底部 stats：Weekly Total / Peak Day / Avg Daily
- 數據來源：Section 12（需 `/fetch-sentio-data` Q12）

### OI History（`oi-history`）
- 折線圖，7 天，前 5 大 OI 幣種各一條線（自動從 Section 8 取 top 5）
- 全零的幣種自動排除（避免無效線條）
- 右側 legend，底部 stats：Week Start / Week End / Change %
- 數據來源：Section 10 Daily OI Snapshot（需 `/fetch-sentio-data` Q10）

### TLP Price（`tlp-price`）
- 折線圖，7 天，mTLP（藍）單線
- Y 軸自動縮放以凸顯波動
- 底部 stats：開盤 → 收盤 + 漲跌幅
- 數據來源：Section 1 Daily Price Snapshot（需 `/fetch-sentio-data` Q1）

### Fee Breakdown（`fee-breakdown`）
- 堆疊長條圖，7 天（Mon–Sun）
- 下層 = Protocol Fee（珊瑚紅），上層 = TLP Fee（藍）
- 底部 stats：週總 TLP Fee / Protocol Fee / 合計 / 峰值日
- 數據來源：Section 13 Daily Fees（需 `/fetch-sentio-data` Q13）

---

## 前置條件

1. Python 3 + matplotlib（已確認：Python 3.13.2、matplotlib 3.10.8）
2. PF Spekk VAR 字型（已安裝於 `~/Library/Fonts/`）
3. Sentio 數據文件存在於 `data-sources/sentio-data/`
   - `volume` 圖需要 Section 12（Q12 daily-volume）
   - `oi-history` 圖需要 Section 10 Daily OI Snapshot（Q10 oi-history）

**可選**：安裝 `cairosvg` 可啟用 SVG logo 浮水印（`pip3 install cairosvg`）

---

## 與其他 Skills 的整合

- **上游**：`/fetch-sentio-data` → 產出 sentio-data MD（包含 Section 10 / 12）
- **呼叫點**：`/weekly-report-prepare` Step 4.6 自動呼叫（或手動執行）
- **下游**：`/publish-medium` 自動上傳 PNG 至 Medium CDN

---

## 擴展新圖表

在 `generate_charts.py` 中新增一個 `chart_XXX(data, output_path)` 函數，並在 `main()` 加入對應的 `--chart` 選項即可。
