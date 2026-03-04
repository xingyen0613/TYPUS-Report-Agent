---
name: weekly-report-prepare
description: Validate weekly report data sources, calculate derived metrics, and produce a structured Weekly Data Brief for report generation.
user-invocable: true
allowed-tools: Read, Glob, Bash, Write, Skill
---

# Typus 週報數據準備與驗算

你是 Typus Finance 週報助手的數據準備模組。你的任務是驗證資料來源、解析原始數據、計算衍生指標，並產生結構化的 Weekly Data Brief 供報告生成使用。

---

## Step 0 — 確認目標週

**情況 A — 被 generate skill 呼叫（帶有 `week_start_date` 參數）**：
- 直接使用傳入的日期

**情況 B — 使用者直接呼叫 `/weekly-report-prepare`**：
- 自動計算前一個完整週（週一至週日）
- 範例：今天 2026-02-10（週二）→ 目標週 2026-02-02（Mon）~ 2026-02-08（Sun）

計算週數與檔名慣例：
```
week_number = (week_start.day - 1) // 7 + 1   # W1=1-7, W2=8-14, W3=15-21, W4=22+
month_name = week_start 月份小寫英文            # "february"
year = week_start 年份                          # 2026
```

向使用者確認：
```
📊 週報數據準備
目標週：Week [N] [Month] [Year]
範圍：[week_start] (Mon) ~ [week_end] (Sun)
```

---

## Step 1 — 驗證資料來源

檢查以下數據源是否存在：

| 來源 | 路徑模式 | 必要性 |
|------|---------|--------|
| Sentio 數據 | `data-sources/sentio-data/week-{N}-{month}-{year}.md` | **必要** |
| 週價格數據 | `data-sources/weekly-prices/week-{N}-{month}-{year}.md` | **必要** |
| 市場參考 | `data-sources/weekly-references/`（當週範圍內的檔案） | 選填（提升市場背景描述） |
| 歷史週報 | `data-sources/weekly-history/` | 選填（風格一致性） |

### 驗證邏輯

1. 使用 Glob 搜尋各路徑下的檔案
2. 對必要檔案：確認存在且內容非空
3. 對選填檔案：記錄可用狀態

### 缺失處理

如有必要數據缺失，報告並建議：
```
⚠️ 數據缺失

❌ Sentio 數據未找到
   → 請先執行 /fetch-sentio-data

❌ 週價格數據未找到
   → 請先執行 /fetch-market-prices（週度模式）

請補充數據後再次執行 /weekly-report-prepare
```

如僅選填數據缺失，標記但繼續執行。但對於市場參考，應提示使用者：
```
⚠️ 市場參考未找到（當週範圍內無 weekly-references 檔案）
   → 建議先執行 /fetch-weekly-references 以獲取最新週報
   → 市場參考可提升報告的市場背景描述品質
```

---

## Step 1.5 — 歷史數據自動補齊

在驗證當週數據後，自動偵測並補齊前 3 週的歷史數據（用於 30 天績效計算）。

### 計算需補的週期

以 `week_start_date`（目標週週一）為基準，往回推算：

```python
# 用 Bash 執行 Python 計算
from datetime import date, timedelta

target_week_start = date(year, month, day)  # 目標週週一

history_weeks = []
for weeks_back in [3, 2, 1]:
    ws = target_week_start - timedelta(weeks=weeks_back)
    we = ws + timedelta(days=6)
    wn = (ws.day - 1) // 7 + 1
    mn = ws.strftime('%B').lower()
    yr = ws.year
    history_weeks.append({
        'week_start': ws.isoformat(),      # e.g. "2026-02-02"
        'week_end': we.isoformat(),        # e.g. "2026-02-08"
        'week_number': wn,                 # e.g. 1
        'month': mn,                       # e.g. "february"
        'year': yr,                        # e.g. 2026
        'label': f"W{wn} {mn.capitalize()[:3]} {yr}"  # e.g. "W1 Feb 2026"
    })
# history_weeks[0] = 3 週前（最舊），history_weeks[2] = 1 週前（最新）
```

### 逐週檢查與補齊（由舊到新）

對 `history_weeks` 中的每一週，依序執行：

1. **用 Glob 確認兩個檔案是否存在**：
   - `data-sources/sentio-data/week-{N}-{month}-{year}.md`
   - `data-sources/weekly-prices/week-{N}-{month}-{year}.md`

2. **如兩個檔案均存在** → 標記為「已存在」，跳過

3. **如有任一檔案缺失** → 依序執行補齊：
   - 若 sentio-data 缺失：呼叫 `fetch-sentio-data` skill，傳入 `week_start_date`
     ```
     呼叫格式：Skill("fetch-sentio-data", "week_start_date: {week_start}")
     ```
   - 若 weekly-prices 缺失：呼叫 `fetch-market-prices` skill，傳入週度模式與日期
     ```
     呼叫格式：Skill("fetch-market-prices", "mode: weekly, date_range: {week_start}")
     ```
   - 若呼叫失敗（API 錯誤）：標記該週為「獲取失敗」，繼續處理下一週（不中斷流程）

### 補齊摘要輸出

```
🔄 歷史數據自動補齊（30 天績效所需）

  W1 Feb 2026（3 週前）：✅ 已存在
  W2 Feb 2026（2 週前）：📥 補齊中... ✅ 完成
  W3 Feb 2026（1 週前）：📥 補齊中... ✅ 完成
  W4 Feb 2026（目標週）：✅ 已存在（當週）

可用歷史週數：4 週 → 30 天績效計算可執行
```

**可用週數規則**：
- ≥ 2 週（含目標週）：進行 30 天累積回報計算
- 1 週（僅目標週）：仍標記「資料不足」
- 補齊失敗的週次：不計入可用週數

補齊完畢後，繼續 Step 2。

---

## Step 2 — 解析原始數據 & 計算衍生指標

從 Sentio 數據文件和價格文件中讀取並計算以下指標：

### A. TLP 回報分析

**來源**：Q1 TLP Price + Q2 Fees + Q5 Trader PnL + Q9 mTLP TVL Composition + Q11 iTLP TVL

計算：
- **mTLP 週回報率** = (收盤價 - 開盤價) / 開盤價
- **iTLP-TYPUS 週回報率** = (收盤價 - 開盤價) / 開盤價
- **mTLP 資產組成**：從 Q9 提取週末快照的 SUI/USDC 權重
  - SUI 權重 = SUI USD 價值 / (SUI USD 價值 + USDC USD 價值)
  - USDC 權重 = 1 - SUI 權重
- **iTLP-TYPUS TVL**：從 Q11 提取週末快照的總 TVL（results[0].matrix.samples[0].values 最後一筆）
  - Total iTLP TVL = 直接讀取 Formula B 的 value
- **回報歸因分解**：
  - Fee Income 貢獻 = TLP Fee / mTLP TVL（或 iTLP TVL）
    - TVL 估算：mTLP TVL ≈ mTLP 價格 × 供應量（如數據可得），否則用 Fee 佔比近似
  - Counterparty PnL 貢獻 = -Trader PnL / TVL（交易者虧 = LP 賺）
  - Basket 效應（僅 mTLP）= 總回報 - Fee 貢獻 - Counterparty 貢獻（殘差法）
  - **Basket 效應驗算**：SUI 週跌幅 × SUI 權重 ≈ Basket 效應（用於交叉驗證殘差法結果）

### B. 交易量摘要

**來源**：Q2 Volume & Fees

提取：
- 週交易量 + WoW 變化（Q2 已計算，直接提取）
- 日均交易量 = 週交易量 / 7
- TLP Fee + Protocol Fee

### C. 幣種交易量分佈

**來源**：Q4 Daily Volume by Token

計算：
- 按幣種匯總 7 天交易量
- 排序：前 5 大幣種
- 各幣種 Long/Short 比例

### D. 交易者盈虧

**來源**：Q5 Daily Traders PnL + Q6 Daily Liquidation

計算：
- 週總 Realized P&L
- 週總清算量
- 日均 P&L
- 標記最大單日盈/虧

### E. 用戶指標

**來源**：Q7 Daily Unique Users

計算：
- 日均 DAU
- 週 DAU 趨勢（上升/下降/持平，比較前半週 vs 後半週）

### F. 持倉快照

**來源**：Q8 Opening Positions

提取：
- 總 OI（Open Interest）
- Long/Short 金額與比例
- 淨曝險 = |Long - Short|
- 未實現 P&L（Trader 視角 + TLP 視角）

### F2. OI 歷史變化

**來源**：Q10 OI History

計算：
- **週初 OI**：取 hour 最早一筆（Mon 00:00 UTC 附近）的 Total
- **週末 OI**：取 hour 最晚一筆（Sun 最後一小時）的 Total
- **OI 週變化** = 週末 OI - 週初 OI（絕對值與百分比）
- **週內峰值**：整週 Total 欄位最大值及其時間戳
- **週內谷值**：整週 Total 欄位最小值及其時間戳
- **Per-Token OI 變化**：對每個幣種（SUI, BTC, ETH, SOL 等）計算週初→週末變化
  - 過濾掉整週 OI 為 0 或 null 的幣種
  - 按週末 OI 降序排列
- **OI 趨勢判斷**：
  - 擴張（expanding）：週末 OI > 週初 OI 且增幅 > 5%
  - 收縮（contracting）：週末 OI < 週初 OI 且減幅 > 5%
  - 持平（stable）：變化在 ±5% 以內

### G. 市場價格

**來源**：weekly-prices 文件

提取：
- BTC/ETH/SOL/SUI 週開盤、收盤、漲跌幅
- 收盤價

### H. 30 天績效比較

**來源**：嘗試讀取前 3-4 週的 Sentio 數據文件和價格文件

計算（如有足夠歷史數據）：
- iTLP-TYPUS 30 天累積回報
- mTLP 30 天累積回報
- SUI 30 天價格變化（來自價格數據）
- Sharpe Ratio 估算（如有 ≥ 4 週數據）：
  - 年化回報 = 週均回報 × 52
  - 年化波動率 = 週回報標準差 × √52
  - Sharpe = 年化回報 / 年化波動率
  - **⚠️ Sharpe 省略條件**：若 mTLP、iTLP、SUI 三者的 30D 累積回報**全部為負**，則不計算 Sharpe，在 brief 中標記：「Sharpe 省略：30D 期間三者報酬均為負，負 Sharpe 不具正向參考意義」
  - 若至少一者為正，正常計算並列出；SUI 的 Sharpe 同樣依此規則決定是否計算
- 如歷史數據不足，標記：「資料不足，需累積更多週數據」

---

## Step 3 — 歷史趨勢標記

如果有前一週或多週數據可用，標記以下趨勢：

- **連續趨勢**：交易量 / TLP 回報 / DAU 連續上升或下降的週數
- **ATH / 歷史低點**：與所有可用歷史週比較，標記新高或新低
- **趨勢反轉**：從上升轉為下降，或反之
- **異常值**：與歷史均值偏差超過 2 倍標準差的指標

如無歷史數據，跳過此步驟並標記「首次生成，無歷史比較」。

---

## Step 4 — 輸出 Weekly Data Brief

產生結構化摘要文件，儲存至：
`data-sources/sentio-data/week-{N}-{month}-{year}-brief.md`

### Data Brief 格式

```markdown
# Weekly Data Brief — Week [N] [Month] [Year]

**生成時間**: [timestamp]
**目標週**: [week_start] (Mon) ~ [week_end] (Sun)
**資料來源**: Sentio Platform + Polygon.io

---

## Key Metrics Summary

| 指標 | 本週 | 上週 | WoW 變化 |
|------|------|------|----------|
| Total Volume | $X.XM | $X.XM | +X% |
| Daily Avg Volume | $X.Xk | — | — |
| TLP Fee | $X.Xk | $X.Xk | +X% |
| Protocol Fee | $X.Xk | $X.Xk | +X% |
| mTLP Return | +X.XX% | +X.XX% | — |
| mTLP TVL | $X.Xk | $X.Xk | +X% |
| iTLP-TYPUS Return | +X.XX% | +X.XX% | — |
| iTLP TVL | $X.Xk | $X.Xk | +X% |
| Trader Realized PnL | -$X.Xk | -$X.Xk | — |
| Total Liquidation | $X.Xk | $X.Xk | — |
| Avg DAU | N | N | +X% |
| Total OI | $X.XM | — | — |
| OI Change (WoW) | $[val] | — | [+/-X%] |

---

## Market Prices

| Token | Week Open | Week Close | Weekly Change |
|-------|-----------|------------|---------------|
| BTC | $XXk | $XXk | +X.X% |
| ETH | $X.Xk | $X.Xk | +X.X% |
| SOL | $XXX | $XXX | +X.X% |
| SUI | $X.XX | $X.XX | +X.X% |

---

## mTLP TVL Composition (週末快照)

- SUI: $[val] ([X.X%])
- USDC: $[val] ([X.X%])
- Total mTLP TVL: $[val]

> mTLP 中 SUI 的權重直接影響 Basket 效應的幅度。SUI 權重越高，SUI 幣價波動對 mTLP 的影響越大。

---

## iTLP-TYPUS TVL (週末快照)

- Total iTLP TVL: $[val]

> iTLP-TYPUS 為 100% USDC 組成，TVL 變動直接反映資金流入／流出情況，不受幣價影響。

---

## TLP Return Attribution

### mTLP (週回報: +X.XX%)
- Fee Income 貢獻: +X.XX%
- Counterparty PnL 貢獻: +X.XX%
- Basket 效應 (SUI 價格): +X.XX%（SUI 權重 [X.X%] × SUI 週跌幅 [X.X%] ≈ 驗算值）

### iTLP-TYPUS (週回報: +X.XX%)
- Fee Income 貢獻: +X.XX%
- Counterparty PnL 貢獻: +X.XX%

---

## Token Volume Distribution

| Token | Total Volume | Share | Long | Short | L/S Ratio |
|-------|-------------|-------|------|-------|-----------|
| [Top 1] | $X.XM | XX% | $X.XM | $X.XM | X.XX |
| [Top 2] | ... | ... | ... | ... | ... |
| [Top 3] | ... | ... | ... | ... | ... |
| [Top 4] | ... | ... | ... | ... | ... |
| [Top 5] | ... | ... | ... | ... | ... |

---

## Trader Performance

| Day | Date | Realized PnL | Liquidation |
|-----|------|-------------|-------------|
| Mon | [date] | $[val] | $[val] |
| Tue | [date] | $[val] | $[val] |
| Wed | [date] | $[val] | $[val] |
| Thu | [date] | $[val] | $[val] |
| Fri | [date] | $[val] | $[val] |
| Sat | [date] | $[val] | $[val] |
| Sun | [date] | $[val] | $[val] |

**週總 Realized PnL**: $[sum]
**週總清算量**: $[sum]
**最大單日盈**: [day] $[val]
**最大單日虧**: [day] $[val]

---

## User Activity

| Day | Date | DAU |
|-----|------|-----|
| Mon | [date] | [N] |
| ... | ... | ... |

**日均 DAU**: [N]
**趨勢**: [上升/下降/持平]

---

## Open Interest Snapshot

| Token | OI Value | Long | Short | Net Exposure | L/S Ratio | Trader PnL | TLP PnL |
|-------|----------|------|-------|-------------|-----------|------------|---------|
| ALL | $[val] | $[val] | $[val] | $[val] | [ratio] | $[val] | $[val] |
| [Per-token rows...] |

---

## OI History (週內 OI 變化)

- **週初 OI**: $[val] (Mon 00:00 UTC)
- **週末 OI**: $[val] (Sun 最後一筆)
- **OI 變化**: $[val] ([+/-X.XX%])
- **OI 趨勢**: [擴張/收縮/持平]
- **週內峰值**: $[val] ([datetime])
- **週內谷值**: $[val] ([datetime])

### Per-Token OI 變化

| Token | 週初 OI | 週末 OI | 變化 | 變化% |
|-------|---------|---------|------|-------|
| SUI | $[val] | $[val] | $[val] | [X%] |
| BTC | $[val] | $[val] | $[val] | [X%] |
| ... | ... | ... | ... | ... |

> OI 數據為每小時粒度，可用於生成 OI 走勢圖表。OI 趨勢結合 Q8 的即時快照，提供更完整的倉位動態分析。

---

## 30-Day Performance Comparison

| Metric | iTLP-TYPUS | mTLP | SUI |
|--------|-----------|------|-----|
| 30D Return | +X.XX% | +X.XX% | +X.X% |
| Annualized Return | +XX.X% | +XX.X% | — |
| Annualized Vol | XX.X% | XX.X% | — |
| Sharpe Ratio | [值 或 省略] | [值 或 省略] | [值 或 省略] |

> Sharpe 規則：若三者 30D 回報全部為負，整列省略並標注「Sharpe 省略：30D 期間三者報酬均為負，負 Sharpe 不具正向參考意義」；若至少一者為正，則三者均計算（SUI 亦同）。
> [如數據不足：「歷史數據不足（僅 [N] 週），需累積至少 4 週數據以計算完整 30 天績效。」]

[Image: 30-Day Comparison Chart]
圖表路徑：outputs/weekly/final/week-[N]-[month]-[year]-30d-performance.png

---

## Historical Trends

- [連續 N 週交易量上升/下降]
- [mTLP 回報創 ATH / 歷史新低]
- [趨勢反轉標記]
- [異常值標記]

> [如無歷史數據：「首次生成，無歷史比較數據。」]

---

## Data Quality Notes

- Sentio 數據: [完整/部分缺失，列出缺失項]
- 價格數據: [完整/部分缺失]
- 市場參考: [可用/不可用]
- 歷史數據: [N 週可用]
- 30天績效: [可計算/數據不足]
```

---

## Step 4.5 — 生成 30 天走勢圖

在 Data Brief 保存後，生成 mTLP / iTLP-TYPUS / SUI 三者的 30 天累積回報走勢圖（PNG）。

### 數據獲取

三條線**全部在圖表生成時直接從 API 即時抓取**，不依賴 weekly-prices 存檔：

| 標的 | 數據源 | API |
|------|--------|-----|
| mTLP | Sentio Metrics | `tlp_price` index=0, step=14400 |
| iTLP-TYPUS | Sentio Metrics | `tlp_price` index=1, step=14400 |
| SUI | CoinGecko 免費 API | `/coins/sui/market_chart/range?from=...&to=...` (hourly, downsampled to 4h) |

> **為何不用 weekly-prices 檔案拼接 SUI？**
> weekly-prices 依賴 fetch-market-prices（需要 ToolSearch + mcp__massive__get_aggs），
> 在 sub-skill context 中無法使用。且存檔可能有缺週，導致曲線斷線。
> CoinGecko 免費 API 無需 key，一次即可取得完整 30 天日線，最簡單可靠。

### 圖表生成（Bash 執行完整 Python 腳本）

```python
import json, urllib.request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone

# ── 參數（由 Step 0 計算得出）───────────────────────────────────────
# week_end_ts = unix_end（目標週結束 Unix timestamp，下週一 00:00 UTC）
# week_number, month_name, year = 目標週週次、月份、年份
chart_start_ts = week_end_ts - 30 * 86400

# ── 1. mTLP / iTLP-TYPUS from Sentio ────────────────────────────────
with open('.claude/skills/fetch-sentio-data/.api-key') as f:
    API_KEY = f.read().strip()

payload = {
    "version": 9,
    "timeRange": {"start": str(chart_start_ts), "end": str(week_end_ts),
                  "step": 14400, "timezone": "UTC"},
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
req = urllib.request.Request(
    "https://api.sentio.xyz/v1/insights/typus/typus_perp/query",
    json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json', 'api-key': API_KEY, 'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req, timeout=60) as r:
    tlp_data = json.loads(r.read())

mtlp_vals = tlp_data['results'][0]['matrix']['samples'][0]['values']
itlp_vals = tlp_data['results'][1]['matrix']['samples'][0]['values']
mtlp_dates  = [datetime.fromtimestamp(int(v['timestamp']), tz=timezone.utc) for v in mtlp_vals]
mtlp_prices = [float(v['value']) for v in mtlp_vals]
itlp_dates  = [datetime.fromtimestamp(int(v['timestamp']), tz=timezone.utc) for v in itlp_vals]
itlp_prices = [float(v['value']) for v in itlp_vals]

# ── 2. SUI from CoinGecko free API（無需 key）───────────────────────
cg_url = f'https://api.coingecko.com/api/v3/coins/sui/market_chart/range?vs_currency=usd&from={chart_start_ts}&to={week_end_ts}'
req2 = urllib.request.Request(cg_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req2, timeout=15) as r2:
    cg = json.loads(r2.read())

# Downsample CoinGecko hourly → 4-hour candles (snap each ts to 4h bucket, keep last)
from collections import OrderedDict
sui_4h = OrderedDict()
for ts_ms, price in cg['prices']:
    bucket = (int(ts_ms / 1000) // 14400) * 14400  # floor to 4h boundary
    sui_4h[bucket] = price  # overwrite → last price in bucket = close

sui_dates  = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in sui_4h]
sui_prices = list(sui_4h.values())

# ── 3. 對齊起始日期（取三者共有的最晚首日）──────────────────────────
common_start = max(mtlp_dates[0], itlp_dates[0], sui_dates[0])
mtlp_d, mtlp_p = zip(*[(d,p) for d,p in zip(mtlp_dates, mtlp_prices) if d >= common_start])
itlp_d, itlp_p = zip(*[(d,p) for d,p in zip(itlp_dates, itlp_prices) if d >= common_start])
sui_d,  sui_p  = zip(*[(d,p) for d,p in zip(sui_dates,  sui_prices)  if d >= common_start])

# ── 4. 標準化累積回報（起始 = 0%）───────────────────────────────────
def norm(prices):
    b = prices[0]
    return [(p/b - 1)*100 for p in prices]

mtlp_ret = norm(mtlp_p)
itlp_ret = norm(itlp_p)
sui_ret  = norm(sui_p)

# ── 5. 繪圖 ─────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 6.5))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#1a1a2e')

ax.plot(mtlp_d, mtlp_ret, color='#4a9eff', linewidth=2.2, label='mTLP',       zorder=3)
ax.plot(itlp_d, itlp_ret, color='#00d4aa', linewidth=2.2, label='iTLP-TYPUS', zorder=3)
ax.plot(sui_d,  sui_ret,  color='#ff8c42', linewidth=2.2, label='SUI',        zorder=3)

ax.axhline(y=0, color='#888899', linewidth=1, linestyle='--', alpha=0.6)
ax.grid(True, color='#2a2a4a', linewidth=0.6, alpha=0.8, zorder=1)

ax.set_xlabel('Date', color='#aaaacc', fontsize=11)
ax.set_ylabel('Cumulative Return (%)', color='#aaaacc', fontsize=11)
ax.set_title(f'30-Day Performance — Week {week_number} {month_name.capitalize()} {year}',
             color='#ffffff', fontsize=14, fontweight='bold', pad=14)

ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=1))
fig.autofmt_xdate(rotation=30)

ax.tick_params(colors='#aaaacc', labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor('#333355')

# 在右側標注最終回報
for dates, rets, color in [(mtlp_d, mtlp_ret, '#4a9eff'),
                            (itlp_d, itlp_ret, '#00d4aa'),
                            (sui_d,  sui_ret,  '#ff8c42')]:
    ax.annotate(f'{rets[-1]:+.1f}%', xy=(dates[-1], rets[-1]),
                xytext=(6, 0), textcoords='offset points',
                color=color, fontsize=10, fontweight='bold', va='center')

ax.legend(loc='lower left', framealpha=0.35, facecolor='#1a1a2e',
          edgecolor='#444466', labelcolor='#ffffff', fontsize=10)

fig.text(0.99, 0.01, 'mTLP/iTLP: Sentio API  |  SUI: CoinGecko',
         ha='right', va='bottom', color='#555577', fontsize=8)

plt.tight_layout()
output_path = f'outputs/weekly/final/week-{week_number}-{month_name}-{year}-30d-performance.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close()
print(f'Chart saved: {output_path}')
```

### 圖表輸出

- **路徑**：`outputs/weekly/final/week-{N}-{month}-{year}-30d-performance.png`
- **解析度**：150 dpi，約 1950×975 px

### 錯誤處理

若 Sentio API 呼叫失敗：
- 標記圖表生成失敗，在 Data Brief 記錄原因，不中斷 Step 5

若 CoinGecko API 失敗（rate limit 或網路問題）：
- 重試一次（等待 5 秒）
- 仍失敗則繪製不含 SUI 的雙線圖，圖例標注「SUI 數據暫不可用」

若 matplotlib 不可用：
- 跳過圖表生成，在 Data Brief 標記「圖表生成失敗，請手動執行」
- 不影響 Step 5 的文字摘要

完成後顯示：
```
📈 30 天走勢圖已生成
   路徑：outputs/weekly/final/week-[N]-[month]-[year]-30d-performance.png
   數據點：mTLP [N] 個 / iTLP-TYPUS [N] 個 / SUI [N] 個
```

---

## Step 5 — 向使用者呈現摘要

讀取已保存的 Data Brief 文件，向使用者輸出以下摘要：

```
📊 Weekly Data Brief — Week [N] [Month] [Year]

Key Metrics:
| 指標 | 本週 | 上週 | WoW |
|------|------|------|-----|
| Volume | $X.XM | $X.XM | +X% |
| TLP Fee | $X.Xk | $X.Xk | +X% |
| mTLP Return | +X.XX% | +X.XX% | — |
| iTLP Return | +X.XX% | +X.XX% | — |
| Trader PnL | -$X.Xk | -$X.Xk | — |
| Avg DAU | N | N | +X% |
| Total OI | $X.XM | — | — |
| OI Change | $[val] | — | [+/-X%] |

Market:
| Token | Close | Weekly Change |
|-------|-------|---------------|
| BTC | $XXk | +X.X% |
| ETH | $X.Xk | +X.X% |
| SOL | $XXX | +X.X% |
| SUI | $X.XX | +X.X% |

📁 Data Brief 已保存至: data-sources/sentio-data/week-[N]-[month]-[year]-brief.md

💡 下一步：運行 /weekly-report-generate 開始撰寫週報
```

等待使用者確認數據正確性。如有問題，協助修正後重新生成 Data Brief。

---

## 數字格式規範

- 百萬美元：~$28.1M（1 位小數）
- 千美元：~$142k（整數）
- 百分比：+29%（整數）或 +2.34%（TLP 回報用 2 位小數）
- 比率：1.42（2 位小數）
- DAU：整數

---

## 注意事項

- 所有計算過程保留完整精度，僅在最終輸出時格式化
- 如某個指標因上游數據缺失無法計算，在 Data Brief 中標記為「N/A — [原因]」
- Data Brief 是 generate skill 的唯一數據入口，必須包含所有報告所需的計算結果
- 不要在 Data Brief 中包含原始時間序列數據，僅保留彙總結果
