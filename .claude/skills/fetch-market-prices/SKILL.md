---
name: fetch-market-prices
description: Automatically fetch historical cryptocurrency prices. Primary: Binance Klines API (no key needed, fast). Fallback: CoinGecko API, then Polygon.io MCP. Supports monthly and weekly modes.
user-invocable: true
allowed-tools: ToolSearch, Read, Write, Bash
---

# 市場價格數據自動獲取（通用版）

你是 Typus Finance 報告助手的價格數據獲取模組。你的任務是根據指定的模式（月度或週度）自動獲取加密貨幣的歷史價格數據。

## 兩種運行模式

此 skill 支援兩種模式，可由**呼叫端 skill 帶參數指定**，或由**使用者直接呼叫時選擇**：

| 參數 | 月度模式 (monthly) | 週度模式 (weekly) |
|------|-------------------|-------------------|
| 時間範圍 | 前一個完整月份 | 指定的一週（週一至週日） |
| 數據間隔 | 4 小時 | 1 小時 |
| 預設幣種 | BTC, ETH, SOL, SUI, XRP | BTC, ETH, SOL, SUI |
| 輸出路徑 | `data-sources/market-prices/{month}-{year}.md` | `data-sources/weekly-prices/week-{N}-{month}-{year}.md` |

---

## 參數定義

當被其他 skill 呼叫時，呼叫端應在 prompt 中指定以下參數：

- **mode**：`monthly` 或 `weekly`（必填）
- **tokens**：幣種清單，例如 `BTC, ETH, SOL, SUI`（選填，有預設值）
- **date_range**：目標日期範圍（選填，會自動計算）
  - 月度：自動取前一完整月
  - 週度：需指定目標週的起始日（週一），或指定 `latest` 自動取前一完整週
- **interval**：數據間隔（選填，有預設值）
  - 月度預設：4 小時
  - 週度預設：1 小時

---

## 執行流程

### Step 0：判斷運行模式

**情況 A — 被其他 skill 呼叫（prompt 中帶有明確參數）**：
- 直接使用 prompt 中提供的 mode、tokens、date_range 等參數
- 不需要詢問使用者，直接執行

**情況 B — 使用者直接呼叫 `/fetch-market-prices`**：
- 詢問使用者要哪種模式：

```
📊 價格數據獲取模式

請選擇模式：
1. 月度模式 (monthly) — 用於月報，獲取前一個完整月份的 4 小時數據
2. 週度模式 (weekly) — 用於週報，獲取指定一週的 1 小時數據

請選擇 (1 或 2)：
```

- 根據選擇確認參數（幣種清單、日期範圍等）

### Step 1：計算時間範圍

#### 月度模式
根據當前日期，自動計算前一個完整月份：
- 今天是 2026-02-03 → 抓取 2026-01-01 至 2026-01-31
- 今天是 2026-03-15 → 抓取 2026-02-01 至 2026-02-28/29

#### 週度模式
計算目標週的日期範圍（**週一至週日**）：
- 若指定 `latest` 或未指定：自動取前一個完整週
  - 今天是 2026-02-10（週二）→ 抓取 2026-02-02（週一）至 2026-02-08（週日）
- 若指定了起始日期：以該日為起點，抓取 7 天
- **週數計算**：使用該週週一所在月份的第幾週（W1 = 第 1-7 天，W2 = 第 8-14 天，W3 = 第 15-21 天，W4+ = 第 22 天起）

向使用者確認：
```
📅 價格數據獲取範圍
模式：[月度/週度]
當前日期：[今天的日期]
目標範圍：[開始日期] 至 [結束日期]
幣種：[BTC, ETH, SOL, ...]
數據間隔：[4 小時 / 1 小時]

繼續獲取價格數據？
```

### Step 2：獲取價格數據

依序嘗試以下三種方式，成功即停止：

---

#### 方式一：Binance K線 API（優先，最穩定）

幣安免費公開 API，無需 API Key，rate limit 寬鬆（1200 req/min）。

**Symbol 對照**：
- BTC: `BTCUSDT` | ETH: `ETHUSDT` | SOL: `SOLUSDT` | SUI: `SUIUSDT` | XRP: `XRPUSDT`

**API Endpoint**：
```
GET https://api.binance.com/api/v3/klines
  ?symbol=BTCUSDT
  &interval=4h          # 月度模式用 4h，週度模式用 1h
  &startTime={ms}       # Unix timestamp 毫秒
  &endTime={ms}
  &limit=1000
```

**Response 格式**：每根 K 線為陣列 `[open_time_ms, open, high, low, close, volume, ...]`
- `[0]` = open_time (ms), `[1]` = open, `[4]` = close

**Python 範例**：
```python
import urllib.request, json
from datetime import datetime, timezone

start_ms = int(datetime(2026, 2, 1, tzinfo=timezone.utc).timestamp() * 1000)
end_ms   = int(datetime(2026, 2, 28, 23, 59, tzinfo=timezone.utc).timestamp() * 1000)

SYMBOLS = [("BTCUSDT","BTC"),("ETHUSDT","ETH"),("SOLUSDT","SOL"),("SUIUSDT","SUI"),("XRPUSDT","XRP")]
all_data = {}

for binance_sym, symbol in SYMBOLS:
    url = f"https://api.binance.com/api/v3/klines?symbol={binance_sym}&interval=4h&startTime={start_ms}&endTime={end_ms}&limit=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        candles = json.loads(r.read())
    # 轉為 [[timestamp_ms, price], ...] 統一格式（用收盤價）
    all_data[symbol] = [[c[0], float(c[4])] for c in candles]
```

**優點**：無需等待，可連續呼叫，5 支幣種秒完成。

---

#### 方式二：CoinGecko API（備用一）

若 Binance 失敗（連線問題、symbol 不存在等），改用 CoinGecko。

**Coin ID 對照**：`bitcoin`, `ethereum`, `solana`, `sui`, `ripple`

**Endpoint**：
```
GET https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range
  ?vs_currency=usd&from={unix_sec}&to={unix_sec}
```

**⚠️ 必須加延遲**：每支幣種間隔 **5 秒**，429 時等 **30 秒**再重試。

---

#### 方式三：Polygon.io MCP（備用二）

若前兩者均失敗，使用 ToolSearch 找 `mcp__massive__get_aggs`，ticker 格式：`X:BTCUSD`。

### Step 4：數據處理與格式化

#### 月度模式 — 週價格彙總 + 詳細數據

將 4 小時數據聚合為每週彙總：
- W1: 第 1-7 天
- W2: 第 8-14 天
- W3: 第 15-21 天
- W4/W5: 第 22 天至月底

每週顯示：開盤價 → 收盤價 (漲跌幅%)

**輸出格式**：

```markdown
# [Month] [Year] Market Prices (4-hour intervals)

**生成時間**: [當前日期時間]
**數據來源**: CoinGecko API
**覆蓋範圍**: [開始日期] ~ [結束日期]
**數據間隔**: 4 小時 (6 數據點/天)

---

## 📊 週價格總結 (Weekly Summary)

用於月報快速參考。

| Week | Period | BTC | ETH | SOL | SUI | XRP |
|------|--------|-----|-----|-----|-----|-----|
| W1 | 1/1-1/7 | $44,200 → $45,100 (+2.0%) | ... | ... | ... | ... |
| W2 | 1/8-1/14 | ... | ... | ... | ... | ... |
| W3 | 1/15-1/21 | ... | ... | ... | ... | ... |
| W4 | 1/22-1/31 | ... | ... | ... | ... | ... |

---

## 📈 詳細價格數據 (4-hour intervals)

### Bitcoin (BTC)

| Date & Time | Open | High | Low | Close | Volume |
|-------------|------|------|-----|-------|--------|
| 2026-01-01 00:00 | $44,150 | $44,280 | $44,100 | $44,200 | 1.2M |
[... 更多數據行 ...]

### Ethereum (ETH)
[同樣格式]

### Solana (SOL)
[同樣格式]

### SUI
[同樣格式]

### XRP
[同樣格式]

---

## 📝 數據使用說明

- **週價格總結**：直接用於月報 "市場價格" 部分
- **詳細數據**：供深度分析使用（可選）
- **價格格式**：已簡化為易讀格式

---

*數據由 Typus 報告助手自動生成*
```

**注意**：表格欄位數量根據實際傳入的幣種清單動態調整。若呼叫端只指定 BTC/ETH/SOL/SUI，則表格只包含這四個幣種。

#### 週度模式 — 每日價格摘要 + 小時級數據

將 1 小時數據聚合為每日摘要 + 保留小時級細節。

**輸出格式**：

```markdown
# Week [N] [Month] [Year] Market Prices (1-hour intervals)

**生成時間**: [當前日期時間]
**數據來源**: CoinGecko API
**覆蓋範圍**: [開始日期（週一）] ~ [結束日期（週日）]
**數據間隔**: 1 小時 (24 數據點/天)
**週數**: Week [N] of [Month] [Year]

---

## 📊 每日價格摘要 (Daily Summary)

用於週報快速參考。

| Day | Date | BTC | ETH | SOL | SUI |
|-----|------|-----|-----|-----|-----|
| Mon | 2/2 | $98,500 → $99,200 (+0.7%) | ... | ... | ... |
| Tue | 2/3 | $99,200 → $98,800 (-0.4%) | ... | ... | ... |
| Wed | 2/4 | ... | ... | ... | ... |
| Thu | 2/5 | ... | ... | ... | ... |
| Fri | 2/6 | ... | ... | ... | ... |
| Sat | 2/7 | ... | ... | ... | ... |
| Sun | 2/8 | ... | ... | ... | ... |

**週開盤 → 週收盤**：
- BTC: $98,500 → $101,200 (+2.7%)
- ETH: $3,150 → $3,280 (+4.1%)
- SOL: $215 → $222 (+3.3%)
- SUI: $4.50 → $4.72 (+4.9%)

---

## 📈 詳細價格數據 (1-hour intervals)

### Bitcoin (BTC)

| Date & Time | Open | High | Low | Close | Volume |
|-------------|------|------|-----|-------|--------|
| 2026-02-02 00:00 | $98,500 | $98,650 | $98,400 | $98,580 | 450K |
| 2026-02-02 01:00 | $98,580 | $98,720 | $98,550 | $98,700 | 380K |
[... 更多數據行 ...]

### Ethereum (ETH)
[同樣格式]

### Solana (SOL)
[同樣格式]

### SUI
[同樣格式]

---

## 📝 數據使用說明

- **每日價格摘要**：直接用於週報 "市場概況" 部分
- **週開盤→收盤**：用於週報標題和關鍵數據
- **詳細數據**：供深度分析使用（可選）

---

*數據由 Typus 報告助手自動生成*
```

### Step 5：保存文件

**月度模式**：
- 路徑：`data-sources/market-prices/{month}-{year}.md`
- 範例：`data-sources/market-prices/january-2026.md`

**週度模式**：
- 路徑：`data-sources/weekly-prices/week-{N}-{month}-{year}.md`
- 範例：`data-sources/weekly-prices/week-1-february-2026.md`
- 週數 N 根據該週週一的日期計算（1-7日=W1, 8-14日=W2, 15-21日=W3, 22+日=W4）

### Step 6：完成報告

向使用者報告執行結果：

```
✅ 市場價格數據獲取完成

📁 文件保存位置：
   [輸出檔案路徑]

📊 數據統計：
   - BTC: [N] 個數據點
   - ETH: [N] 個數據點
   - SOL: [N] 個數據點
   - SUI: [N] 個數據點
   [- XRP: [N] 個數據點]（月度模式時）
   - 總計: [N] 個數據點

📅 覆蓋時間：
   [開始日期] 至 [結束日期]

💡 下一步：
   [月度] 運行 /monthly-report-generate 開始撰寫月報
   [週度] 運行 /weekly-report-generate 開始撰寫週報
```

## 錯誤處理

如果 API 調用失敗或數據不完整：

```
⚠️ 價格數據獲取遇到問題

問題詳情：
[具體錯誤信息]

建議：
1. 檢查 API 連接狀態
2. 確認日期範圍是否有效
3. 可以選擇手動提供價格數據

手動提供格式示例：
[月度]
W1 (1/1-1/7): BTC $44.2k → $45.1k, ETH $2.45k → $2.52k, SOL $210 → $215, ...
W2 (1/8-1/14): BTC $45.1k → $46.8k, ETH $2.52k → $2.68k, SOL $215 → $225, ...

[週度]
Mon (2/2): BTC $98.5k → $99.2k, ETH $3.15k → $3.18k, SOL $215 → $217, ...
Tue (2/3): BTC $99.2k → $98.8k, ETH $3.18k → $3.16k, SOL $217 → $216, ...
```

## 注意事項

- 優先使用 API 自動獲取
- 價格使用 USD 計價
- 數據格式必須與對應的報告生成模組兼容
- 保持數據的一致性和可讀性
- 幣種清單根據呼叫端指定動態調整，不硬編碼
