# Sentio Data Schema — 總覽

> 此文件記錄 Sentio 平台的 API 共用規格、通用回傳結構、欄位對照總表。
> 各 query 的詳細 payload 和欄位說明請見 `queries/` 目錄下的個別檔案。

## API 連接方式

Sentio 有**兩種 API endpoint**，不同 query 使用不同的 endpoint：

### Metrics Endpoint（時間序列資料）
- **URL**: `https://api.sentio.xyz/v1/insights/typus/typus_perp/query`
- **用途**: 取得隨時間變化的指標（如價格走勢）
- **時間格式**: Unix timestamp (秒)
- **回傳格式**: `results[].matrix.samples[].values[]` 時間序列

### SQL Endpoint（聚合表格資料）
- **URL**: `https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute`
- **用途**: 執行 SQL 查詢取得聚合後的表格數據（如週交易量、手續費）
- **時間格式**: `toDateTime('YYYY-MM-DD HH:MM:SS', 'UTC')`
- **回傳格式**: `result.{columns, columnTypes, rows[]}` 表格
### 共用設定
- **Method**: `POST`
- **認證方式**: API Key（透過 Header 傳遞）
- **認證 Header**: `api-key: <API_KEY>`
- **Content-Type**: `application/json`
- **必要 Header**: `User-Agent: Mozilla/5.0`（兩種 endpoint 都需要，否則可能被 Cloudflare 擋 403）

---

## 時間範圍格式

### Metrics Endpoint（Query 1 等）
使用 **Unix timestamp (秒) + UTC timezone**：
```json
"timeRange": {
  "start": "<UNIX_TIMESTAMP>",
  "end": "<UNIX_TIMESTAMP>",
  "step": 3600,
  "timezone": "UTC"
}
```

### SQL Endpoint（Query 2 等）
使用 **toDateTime 格式**：
```json
"variables": {
  "startTime": "toDateTime('2026-02-02 08:00:00', 'UTC')",
  "endTime": "toDateTime('2026-02-09 08:00:00', 'UTC')"
}
```

### 共通規則
- 目標範圍：**週一 00:00 UTC** 至 **下週一 00:00 UTC**（7 天）
- 時間計算由上層呼叫端 skill（`weekly-report-generate`）負責，`fetch-sentio-data` 接收已算好的時間參數

---

## 回傳結構對比

### Metrics Endpoint（時間序列）
```
results[]
  ├── id / alias
  ├── dataSource: "METRICS"
  └── matrix.samples[].values[]
      ├── timestamp  (string, unix 秒)
      └── value      (float)
```

### SQL Endpoint（表格）
```
result
  ├── columns      (string[])
  ├── columnTypes   (object)
  └── rows[]        (object[])
```

---

## 欄位對照表（彙總）

| Sentio 欄位 | 週報指標名稱 | 單位 | 來源 Query |
|-------------|-------------|------|-----------|
| `tlp_price` (index=0) | mTLP Price | USD | Query 1 (tlp-price) |
| `tlp_price` (index=1) | iTLP-TYPUS Price | USD | Query 1 (tlp-price) |
| `total_vol` | Weekly Volume | USD | Query 2 (volume-and-fees) |
| `daily_vol` | Daily Avg Volume | USD | Query 2 (volume-and-fees) |
| `vol_change` / `vol_pct` | Volume WoW Change | USD / % | Query 2 (volume-and-fees) |
| `TLPFee` | TLP Fee (iTLP+mTLP) | USD | Query 2 (volume-and-fees) |
| `TLPFee_change` / `TLPFee_pct` | TLP Fee WoW Change | USD / % | Query 2 (volume-and-fees) |
| `ProtocolFee` | Protocol Fee | USD | Query 2 (volume-and-fees) |
| `ProtocolFee_change` / `ProtocolFee_pct` | Protocol Fee WoW Change | USD / % | Query 2 (volume-and-fees) |
| `Vol` (formula) | Cumulative Volume | USD | Query 3 (cumulative-volume) |
| `trading_volume_usd` (grouped) | Daily Volume by Token & Side | USD | Query 4 (daily-volume-by-token) |
| `Daily_PnlUSD` | Daily Traders P&L | USD | Query 5 (daily-traders-pnl) |
| `vol` (liquidation) | Daily Liquidation Volume | USD | Query 6 (daily-liquidation-volume) |
| `<All Events> - DAU` | Daily Unique Users | count | Query 7 (daily-unique-users) |
| `TotalValue` | Open Interest Value | USD | Query 8 (opening-positions) |
| `Long_Value` / `Short_Value` | Long/Short OI | USD | Query 8 (opening-positions) |
| `Net_Exposure_Side` | LP Net Exposure | USD | Query 8 (opening-positions) |
| `L_S_Ratio` | Long/Short Ratio | — | Query 8 (opening-positions) |
| `TraderPnlUSD` / `PnlUSDForTLP` | Unrealized P&L | USD | Query 8 (opening-positions) |
| `tvl` × price (formula A, grouped by `coin_symbol`) | mTLP TVL per Coin (USD) | USD | Query 9 (mtlp-tvl-composition) |
| — (derived) | SUI Weight in mTLP | % | Query 9 (mtlp-tvl-composition) |
| `Total` (OI hourly) | Total OI (hourly) | USD | Query 10 (oi-history) |
| `BTC`/`ETH`/`SOL`/`SUI`/... (OI) | Per-Token OI (hourly) | USD | Query 10 (oi-history) |

> 此表隨新 query 加入持續更新。

---

## 查詢清單

| # | 檔案 | 名稱 | Endpoint | 用途 |
|---|------|------|----------|------|
| 1 | `queries/tlp-price.md` | TLP Price | Metrics | mTLP 和 iTLP-TYPUS 價格走勢 |
| 2 | `queries/volume-and-fees.md` | Volume & Fees | SQL | 週交易量、日均量、WoW 變化、手續費分配 |
| 3 | `queries/cumulative-volume.md` | Cumulative Volume | Metrics | 累積總交易量（固定用 now-1h，取最新值） |
| 4 | `queries/daily-volume-by-token.md` | Daily Volume by Token & Side | Metrics | 每日各幣種各方向交易量（step=86400） |
| 5 | `queries/daily-traders-pnl.md` | Daily Traders P&L | SQL | 每日交易者淨盈虧（**時間寫在 SQL 中**） |
| 6 | `queries/daily-liquidation-volume.md` | Daily Liquidation Volume | SQL (LITE) | 每日清算量，排除刷量地址（搭配 Q5 看） |
| 7 | `queries/daily-unique-users.md` | Daily Unique Users | Metrics | 每日不重複地址用戶數 DAU（step=86400） |
| 8 | `queries/opening-positions.md` | Opening Positions | SQL | 當前各交易對持倉快照：OI、多空、曝險、未實現 P&L |
| 9 | `queries/mtlp-tvl-composition.md` | mTLP TVL Composition | Metrics | mTLP 各幣種（SUI/USDC）USD 價值，用於計算 SUI 權重與 Basket 效應 |
| 10 | `queries/oi-history.md` | OI History | SQL | 每小時各幣種 OI 歷史變化（累積式，含向前填補） |

---

## 注意事項

- Metrics endpoint 和 SQL endpoint 的時間參數格式不同，注意區分
- **兩種 endpoint 都需要** `User-Agent: Mozilla/5.0` header（Cloudflare 防護）
- `step: 3600` 對應 1 小時間隔，適合週報使用
- Metrics 資料中部分時段的 value 可能重複（無鏈上事件時不更新）
- SQL query 內已自帶 WoW 對比邏輯，不需額外計算
- SUI 幣價不從 Sentio 取，改由 `fetch-market-prices` skill 獲取

---

*建立於 2026-02-10，持續更新中。*
