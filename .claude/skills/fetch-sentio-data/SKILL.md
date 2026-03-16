---
name: fetch-sentio-data
description: Fetch Typus Protocol on-chain data from Sentio platform for weekly report. Executes multiple queries to retrieve TLP prices, volume, fees, P&L, users, and position data.
user-invocable: true
allowed-tools: ToolSearch, Read, Write, Bash
---

# Sentio 平台數據獲取

你是 Typus Finance 週報助手的 Sentio 數據獲取模組。你的任務是從 Sentio 平台 API 抓取週報所需的各項鏈上數據。

## 參考文件

執行前請先讀取以下文件：
- **Schema 總覽**：`.claude/skills/fetch-sentio-data/SENTIO-SCHEMA.md`
- **各 Query 定義**：`.claude/skills/fetch-sentio-data/queries/*.md`

## 參數定義

當被其他 skill 呼叫時，呼叫端應在 prompt 中指定：

- **week_start_date**：目標週的週一日期，格式 `YYYY-MM-DD`（必填）
- **unix_start**：週一 00:00 UTC 的 Unix timestamp（選填，會自動計算）
- **unix_end**：下週一 00:00 UTC 的 Unix timestamp（選填，會自動計算）

當使用者直接呼叫 `/fetch-sentio-data` 時：
- 詢問目標週日期，或自動取前一個完整週（前一個週一到週日）

---

## 執行流程

### Step 0：確認時間參數

**情況 A — 被其他 skill 呼叫（帶有參數）**：
- 直接使用傳入的時間參數

**情況 B — 使用者直接呼叫**：
- 根據當前日期計算前一個完整週
- 範例：今天 2026-02-10（週二）→ 目標週 2026-02-02（Mon）~ 2026-02-08（Sun）

向使用者確認：
```
📊 Sentio 數據獲取範圍
目標週：[week_start_date] (Mon) ~ [week_end_date] (Sun)
```

### Step 1：計算各種時間格式

根據 `week_start_date` 計算所有 query 需要的時間格式：

```python
# 用 Bash 執行 Python 計算
import datetime

week_start = datetime.datetime(2026, 2, 2, tzinfo=datetime.timezone.utc)  # 週一 00:00 UTC
week_end = week_start + datetime.timedelta(days=7)  # 下週一 00:00 UTC

# Metrics endpoint 用（Query 1, 3, 4, 7, 9）
unix_start = int(week_start.timestamp())          # "1769990400"
unix_end = int(week_end.timestamp())              # "1770595200"

# SQL endpoint 用（Query 2, 5, 6）
sql_start = week_start.strftime('%Y-%m-%d %H:%M:%S')  # "2026-02-02 00:00:00"
sql_end = week_end.strftime('%Y-%m-%d %H:%M:%S')      # "2026-02-09 00:00:00"

# 週數計算
week_number = (week_start.day - 1) // 7 + 1  # W1, W2, W3, W4
month_name = week_start.strftime('%B').lower()  # "february"
year = week_start.year  # 2026
```

### Step 2：讀取 API Key

從 `.claude/skills/fetch-sentio-data/.api-key` 檔案讀取（此檔案已加入 `.gitignore`，不會被 git 追蹤）。

```python
with open('.claude/skills/fetch-sentio-data/.api-key') as f:
    API_KEY = f.read().strip()
```

如檔案為空或不存在，提示使用者填入：
```
⚠️ Sentio API Key 未設定

請將 API Key 寫入以下檔案（一行即可）：
.claude/skills/fetch-sentio-data/.api-key

此檔案已加入 .gitignore，不會被上傳。
```

### Step 3：依序執行各 Query

使用 Bash 執行 Python（`urllib`）打 API。**所有請求必須帶 `User-Agent: Mozilla/5.0` header。**

#### 執行順序與時間參數對照

| # | Query 文件 | Endpoint | 時間處理 | Engine |
|---|-----------|----------|---------|--------|
| 1 | `queries/tlp-price.md` | Metrics | `timeRange.start/end` = Unix timestamp, `step=3600` | — |
| 2 | `queries/volume-and-fees.md` | SQL | `variables.startTime/endTime` = `toDateTime(...)` | DEFAULT |
| 3 | `queries/cumulative-volume.md` | Metrics | `timeRange.start = unix_end - 3600, end = unix_end`（取週末快照） | — |
| 4 | `queries/daily-volume-by-token.md` | Metrics | `timeRange.start/end` = Unix timestamp, `step=86400` | — |
| 5 | `queries/daily-traders-pnl.md` | SQL | **SQL 字串替換**：WHERE 子句中的日期 | DEFAULT |
| 6 | `queries/daily-liquidation-volume.md` | SQL | **SQL 字串替換**：WHERE 子句中的日期 | LITE |
| 7 | `queries/daily-unique-users.md` | Metrics | `timeRange.start/end` = Unix timestamp, `step=86400` | — |
| 8 | `queries/opening-positions.md` | SQL | **即時快照**（不需動態時間） | DEFAULT |
| 9 | `queries/mtlp-tvl-composition.md` | Metrics | `timeRange.start/end` = Unix timestamp, `step=86400` | — |
| 10 | `queries/oi-history.md` | SQL | **SQL 字串替換**：`{{START_TIME}}`/`{{END_TIME}}` | DEFAULT |
| 11 | `queries/itlp-tvl.md` | Metrics | `timeRange.start/end` = Unix timestamp, `step=86400` | — |
| 12 | `queries/daily-volume.md` | Metrics | `timeRange.start/end` = Unix timestamp, `step=86400` | — |
| 13 | `queries/daily-fees.md` | SQL | **SQL 字串替換**：`{{START_TIME}}`/`{{END_TIME}}` | DEFAULT |

#### API 呼叫範本

**Metrics endpoint**（Query 1, 3, 4, 7, 9, 11, 12）：
```python
import json, urllib.request

url = "https://api.sentio.xyz/v1/insights/typus/typus_perp/query"
# payload 從各 query 文件取得，替換時間參數
req = urllib.request.Request(url, json.dumps(payload).encode('utf-8'), headers={
    'Content-Type': 'application/json',
    'api-key': '<API_KEY>',
    'User-Agent': 'Mozilla/5.0'
})
with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read())
```

**SQL endpoint**（Query 2, 5, 6, 8）：
```python
url = "https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute"
# 同上，注意 SQL 字串中的時間替換
```

#### SQL 時間替換規則

**Query 2**（volume-and-fees）：替換 `variables` 中的 startTime/endTime
```python
payload["sqlQuery"]["variables"]["startTime"] = f"toDateTime('{sql_start}', 'UTC')"
payload["sqlQuery"]["variables"]["endTime"] = f"toDateTime('{sql_end}', 'UTC')"
```

**Query 5, 6, 10, 13**（daily-traders-pnl, daily-liquidation-volume, oi-history, daily-fees）：替換 SQL WHERE 子句中的日期
```python
sql = sql.replace("{{START_TIME}}", sql_start)
sql = sql.replace("{{END_TIME}}", sql_end)
```

> Query 10 特別注意：`{{END_TIME}}` 過濾 event CTE 的事件上限（避免累積 OI 包含目標週之後的事件），並過濾最終輸出只顯示目標週的小時數據。

### Step 4：處理回傳數據

為每個 query 的回傳數據做基本處理：

**Metrics 回傳**（時間序列）：
- 提取 `results[].matrix.samples[].values[]`
- 將 Unix timestamp 轉為可讀日期

**SQL 回傳**（表格）：
- 提取 `result.rows[]`
- 驗證欄位是否完整

### Step 5：格式化為結構化 Markdown

將所有數據彙整為一份 Markdown 文件，格式如下：

```markdown
# Typus Perp Weekly Data — Week [N] [Month] [Year]

**生成時間**: [當前日期時間]
**數據來源**: Sentio Platform API
**覆蓋範圍**: [week_start] (Mon) ~ [week_end] (Sun)

---

## 1. TLP Price（TLP 價格走勢）

### mTLP
- 週開盤: $[value] | 週收盤: $[value] | 變化: [+/-X.XX%]

### iTLP-TYPUS
- 週開盤: $[value] | 週收盤: $[value] | 變化: [+/-X.XX%]

### Daily Price Snapshot（每日收盤價，取每日最後一筆）

| Day | Date | mTLP | iTLP-TYPUS |
|-----|------|------|------------|
| Mon | [date] | $[val] | $[val] |
| Tue | [date] | $[val] | $[val] |
| Wed | [date] | $[val] | $[val] |
| Thu | [date] | $[val] | $[val] |
| Fri | [date] | $[val] | $[val] |
| Sat | [date] | $[val] | $[val] |
| Sun | [date] | $[val] | $[val] |

> 從 Q1 回傳的小時序列（step=3600）中，按日分組取最後一筆 value 作為當日收盤價。

---

## 2. Volume & Fees（交易量與手續費）

| 指標 | 本週 | 上週 | 變化 | 變化% |
|------|------|------|------|-------|
| Total Volume | $[val] | $[val] | $[val] | [X%] |
| Daily Avg Volume | $[val] | — | — | — |
| TLP Fee | $[val] | $[val] | $[val] | [X%] |
| Protocol Fee | $[val] | $[val] | $[val] | [X%] |

---

## 3. Cumulative Volume（累積交易量）

**當前累積交易量**: $[value]

---

## 4. Daily Volume by Token & Side（每日幣種方向交易量）

| Token | Long | Short | Liquidate | Total |
|-------|------|-------|-----------|-------|
| SUI | $[val] | $[val] | $[val] | $[val] |
| ... | ... | ... | ... | ... |

---

## 5. Daily Traders P&L（每日交易者盈虧）

| Day | Date | P&L (USD) |
|-----|------|-----------|
| Mon | [date] | $[val] |
| ... | ... | ... |

**週總 P&L**: $[sum]

---

## 6. Daily Liquidation Volume（每日清算量）

| Day | Date | Liquidation (USD) |
|-----|------|-------------------|
| Mon | [date] | $[val] |
| ... | ... | ... |

**週總清算**: $[sum]

---

## 7. Daily Unique Users（每日不重複用戶）

| Day | Date | DAU |
|-----|------|-----|
| Mon | [date] | [N] |
| ... | ... | ... |

**日均用戶**: [avg]

---

## 8. Opening Positions（當前持倉快照）

| Token | OI Value | Long | Short | Net Exposure | L/S Ratio | Trader P&L | TLP P&L |
|-------|----------|------|-------|-------------|-----------|------------|---------|
| ALL | $[val] | $[val] | $[val] | $[val] | [ratio] | $[val] | $[val] |
| SUI | $[val] | $[val] | $[val] | $[val] | [ratio] | $[val] | $[val] |
| ... | ... | ... | ... | ... | ... | ... | ... |

---

## 9. mTLP TVL Composition（mTLP 資產組成）

**週末快照（[date]）**：
- SUI: $[val] ([X.X%])
- USDC: $[val] ([X.X%])
- Total mTLP TVL: $[val]

---

## 10. OI History（OI 歷史變化）

**週初 OI (Mon 00:00 UTC)**: Total $[val] | SUI $[val] | BTC $[val] | ...
**週末 OI (Sun 最後一筆)**: Total $[val] | SUI $[val] | BTC $[val] | ...
**OI 變化**: $[val] ([+/-X.XX%])
**週內峰值**: $[val] ([datetime])
**週內谷值**: $[val] ([datetime])

### Per-Token OI 變化

| Token | 週初 OI | 週末 OI | 變化 | 變化% |
|-------|---------|---------|------|-------|
| SUI | $[val] | $[val] | $[val] | [X%] |
| BTC | $[val] | $[val] | $[val] | [X%] |
| ... | ... | ... | ... | ... |

### Daily OI Snapshot（每日 OI 快照，取每日 23:00 UTC）

| Date | Total | SUI | WAL | DEEP | BTC | TYPUS | ETH | SPYX | QQQX | NVDAX | APT | SOL | JPY | XAG | XRP | HYPE | DOGE | TSLAX | XAU | USOIL | BNB |
|------|-------|-----|-----|------|-----|-------|-----|------|------|-------|-----|-----|-----|-----|-----|------|------|-------|-----|-------|-----|
| 2026-02-02 | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] |
| 2026-02-03 | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] |
| 2026-02-04 | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] |
| 2026-02-05 | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] |
| 2026-02-06 | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] |
| 2026-02-07 | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] |
| 2026-02-08 | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] | $[v] |

> 每日快照取該日 23:00 UTC（UTC+8 = 07:00 隔日）的 OI 值；若該小時無資料，取最近一筆向前填補值。

---

## 11. iTLP-TYPUS TVL（iTLP 資金池總鎖定價值）

**週末快照（[date]）**：
- Total iTLP TVL: $[val]

> iTLP-TYPUS 為 100% USDC 組成，TVL 直接反映資金規模。

---

## 12. Daily Total Volume（每日總交易量）

| Day | Date | Volume (USD) |
|-----|------|--------------|
| Mon | [date] | $[val] |
| Tue | [date] | $[val] |
| Wed | [date] | $[val] |
| Thu | [date] | $[val] |
| Fri | [date] | $[val] |
| Sat | [date] | $[val] |
| Sun | [date] | $[val] |

**週總交易量**: $[sum]

---

## 13. Daily Fees（每日手續費明細）

| Day | Date | TLP Fee (USD) | Protocol Fee (USD) |
|-----|------|---------------|-------------------|
| Mon | [date] | $[val] | $[val] |
| Tue | [date] | $[val] | $[val] |
| Wed | [date] | $[val] | $[val] |
| Thu | [date] | $[val] | $[val] |
| Fri | [date] | $[val] | $[val] |
| Sat | [date] | $[val] | $[val] |
| Sun | [date] | $[val] | $[val] |

**週總 TLP Fee**: $[sum] | **週總 Protocol Fee**: $[sum]

---

*數據由 Typus 週報助手自動從 Sentio 平台獲取*
```

### Step 6：儲存文件

路徑：`data-sources/sentio-data/week-{N}-{month}-{year}.md`

範例：`data-sources/sentio-data/week-1-february-2026.md`

### Step 7：完成報告

```
✅ Sentio 數據獲取完成

📁 文件保存位置：
   data-sources/sentio-data/[filename]

📊 數據統計：
   - Q1 TLP Price: mTLP [開盤→收盤], iTLP [開盤→收盤]
   - Q2 Volume: $[weekly_vol] (WoW [+/-X%])
   - Q3 Cumulative Volume: $[cum_vol]
   - Q4 Top Trading Pair: [token] ($[vol])
   - Q5 Traders P&L: $[weekly_pnl]
   - Q6 Liquidations: $[weekly_liq]
   - Q7 Avg DAU: [N]
   - Q8 Total OI: $[oi] (L/S: [ratio])
   - Q9 mTLP Composition: SUI [X%] / USDC [X%]
   - Q10 OI History: 週初 $[start_oi] → 週末 $[end_oi] ([+/-X%])
   - Q11 iTLP TVL: $[val]
   - Q12 Daily Volume: 週一 $[mon_vol] ~ 週日 $[sun_vol]，週總 $[total_vol]
   - Q13 Daily Fees: TLP Fee 週總 $[val]，Protocol Fee 週總 $[val]

💡 下一步：
   運行 /weekly-report-generate 開始撰寫週報
```

---

## 錯誤處理

如果某個 query 失敗：
1. 記錄錯誤訊息
2. 繼續執行其餘 query（不中斷）
3. 在輸出文件中標記該 query 為「獲取失敗」
4. 在完成報告中列出失敗項目及建議

常見錯誤：
- **403 Forbidden**：檢查是否帶了 `User-Agent: Mozilla/5.0` header
- **Timeout**：SQL query 可能較慢，timeout 設為 60 秒
- **Empty result**：某些日期可能無數據（如無清算事件），屬正常

---

## 注意事項

- **所有 API 請求必須帶 `User-Agent: Mozilla/5.0`**（Cloudflare 防護）
- Query 8（持倉快照）不需要動態時間參數；Query 3（累積交易量）需使用 `unix_end - 3600` / `unix_end` 取週末快照
- SQL query 有兩種 engine：大部分用 `DEFAULT`，Query 6 用 `LITE`
- SQL 時間替換：Query 2 用 `variables`；Query 5、6、10 直接字串替換 `{{START_TIME}}`/`{{END_TIME}}`
- Query 10（OI History）：`{{END_TIME}}` 同時作為事件上限（`event` CTE WHERE）和輸出範圍過濾（最終 SELECT WHERE），確保不包含目標週之後的數據
- Query 11（iTLP TVL）：使用 `index: "1"`（iTLP 池）；Formula A disabled，Formula B（sum）enabled；回傳 results[0] = 總 TVL
- 金額顯示保留 2 位小數，大數字用千分位分隔
