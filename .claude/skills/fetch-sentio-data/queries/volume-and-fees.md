# Query 2: Volume & Fees（交易量與手續費）

**用途**：獲取每週總交易量、日均交易量、交易量變化（WoW），以及手續費分配（TLP Fee vs Protocol Fee）與上週對比。單位均為 USD。

**API Endpoint**：`https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute`
> 注意：此 query 使用 **SQL endpoint**（`/analytics/.../sql/execute`），與 Query 1 的 Metrics endpoint 不同。

---

## 請求 Payload

```json
{
  "version": 9,
  "sqlQuery": {
    "sql": "<SQL_CONTENT>",
    "variables": {
      "startTime": "toDateTime('<YYYY-MM-DD HH:MM:SS>', 'UTC')",
      "endTime": "toDateTime('<YYYY-MM-DD HH:MM:SS>', 'UTC')"
    },
    "size": 100
  },
  "source": "DASHBOARD",
  "cachePolicy": {
    "noCache": false,
    "cacheTtlSecs": 43200,
    "cacheRefreshTtlSecs": 1800
  },
  "engine": "DEFAULT"
}
```

### 時間參數格式

SQL endpoint 的時間格式與 Metrics endpoint 不同：
- **不是** Unix timestamp
- 使用 `toDateTime('YYYY-MM-DD HH:MM:SS', 'UTC')` 格式
- 範例：`"startTime": "toDateTime('2026-02-02 08:00:00', 'UTC')"`

### 完整 SQL

```sql
-- 合併 volume 資料
WITH merged_vol AS (
  SELECT timestamp, filled_price * filled_size AS volusd
  FROM OrderFilled
  UNION ALL
  SELECT timestamp, position_size * trading_price AS volusd
  FROM Liquidate
),

-- 合併 fee 資料
merged_fee AS (
  SELECT
    timestamp AS time,
    toDecimal64(realized_fee_in_usd * 0.7, 8) AS TLPFee,
    toDecimal64(realized_fee_in_usd * 0.3, 8) AS ProtocolFee
  FROM OrderFilled
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(realized_funding_fee_usd, 8) AS TLPFee,
    toDecimal64(0, 8) AS ProtocolFee
  FROM RealizeFunding
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(fee_usd * 0.7, 8) AS TLPFee,
    toDecimal64(fee_usd * 0.3, 8) AS ProtocolFee
  FROM RealizeOption
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(0, 8) AS TLPFee,
    toDecimal64(mint_fee_usd, 8) AS ProtocolFee
  FROM MintLp
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(0, 8) AS TLPFee,
    toDecimal64(burn_fee_usd, 8) AS ProtocolFee
  FROM BurnLp
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(fee_amount_usd * 0.7, 8) AS TLPFee,
    toDecimal64(fee_amount_usd * 0.3, 8) AS ProtocolFee
  FROM Swap
),

-- 聚合每週交易量
weekly_summary AS (
  SELECT
    toStartOfWeek(timestamp, 1) AS week_start,
    round(sum(volusd), 2) AS total_vol,
    round(sum(volusd) / 7, 2) AS daily_vol
  FROM merged_vol
  GROUP BY week_start
),

-- 聚合每週費用
weekly_fee AS (
  SELECT
    toStartOfWeek(time, 1) AS week_start,
    round(sum(TLPFee), 2) AS TLPFee,
    round(sum(ProtocolFee), 2) AS ProtocolFee
  FROM merged_fee
  GROUP BY week_start
),

-- 整合每週交易量與費用
weekly_all AS (
  SELECT
    s.week_start,
    s.total_vol,
    s.daily_vol,
    f.TLPFee,
    f.ProtocolFee
  FROM weekly_summary s
  LEFT JOIN weekly_fee f ON s.week_start = f.week_start
)

-- 最終輸出結果，含變化與百分比（使用 Decimal128 防止 overflow）
SELECT
  curr.week_start,
  curr.total_vol,
  curr.daily_vol,
  round(curr.total_vol - prev.total_vol, 2) AS vol_change,
  CASE
    WHEN prev.total_vol = 0 OR prev.total_vol IS NULL THEN '-'
    ELSE concat(toString(round(
      (CAST(curr.total_vol AS Decimal128(8)) - CAST(prev.total_vol AS Decimal128(8)))
      / NULLIF(CAST(prev.total_vol AS Decimal128(8)), 0) * 100, 2)), '%')
  END AS vol_pct,

  curr.TLPFee,
  round(curr.TLPFee - prev.TLPFee, 2) AS TLPFee_change,
  CASE
    WHEN prev.TLPFee = 0 OR prev.TLPFee IS NULL THEN '-'
    ELSE concat(toString(round(
      (CAST(curr.TLPFee AS Decimal128(8)) - CAST(prev.TLPFee AS Decimal128(8)))
      / NULLIF(CAST(prev.TLPFee AS Decimal128(8)), 0) * 100, 2)), '%')
  END AS TLPFee_pct,

  curr.ProtocolFee,
  round(curr.ProtocolFee - prev.ProtocolFee, 2) AS ProtocolFee_change,
  CASE
    WHEN prev.ProtocolFee = 0 OR prev.ProtocolFee IS NULL THEN '-'
    ELSE concat(toString(round(
      (CAST(curr.ProtocolFee AS Decimal128(8)) - CAST(prev.ProtocolFee AS Decimal128(8)))
      / NULLIF(CAST(prev.ProtocolFee AS Decimal128(8)), 0) * 100, 2)), '%')
  END AS ProtocolFee_pct

FROM weekly_all AS curr
LEFT JOIN weekly_all AS prev
  ON curr.week_start = prev.week_start + INTERVAL 7 DAY
ORDER BY curr.week_start DESC
```

---

## 回傳欄位

| 欄位 | 類型 | 單位 | 說明 | 週報指標 |
|------|------|------|------|---------|
| `week_start` | TIME | — | 週起始日（ISO 8601 格式） | 週標識 |
| `total_vol` | NUMBER | USD | 本週總交易量 | Weekly Volume |
| `daily_vol` | NUMBER | USD | 本週日均交易量（total_vol / 7） | Daily Avg Volume |
| `vol_change` | NUMBER | USD | 交易量變化（本週 - 上週） | Volume WoW Change |
| `vol_pct` | STRING | % | 交易量變化百分比 | Volume WoW % |
| `TLPFee` | NUMBER | USD | TLP 手續費（iTLP + mTLP 用戶分到的） | TLP Fee |
| `TLPFee_change` | NUMBER | USD | TLP 手續費變化（本週 - 上週） | TLP Fee WoW Change |
| `TLPFee_pct` | STRING | % | TLP 手續費變化百分比 | TLP Fee WoW % |
| `ProtocolFee` | NUMBER | USD | Protocol 手續費（平台分到的） | Protocol Fee |
| `ProtocolFee_change` | NUMBER | USD | Protocol 手續費變化（本週 - 上週） | Protocol Fee WoW Change |
| `ProtocolFee_pct` | STRING | % | Protocol 手續費變化百分比 | Protocol Fee WoW % |

---

## 回傳結構

SQL endpoint 回傳**表格式**資料（與 Metrics endpoint 的時間序列格式不同）：

```json
{
  "runtimeCost": "592",
  "result": {
    "columns": [
      "week_start", "total_vol", "daily_vol", "vol_change", "vol_pct",
      "TLPFee", "TLPFee_change", "TLPFee_pct",
      "ProtocolFee", "ProtocolFee_change", "ProtocolFee_pct"
    ],
    "columnTypes": {
      "week_start": "TIME",
      "total_vol": "NUMBER",
      "daily_vol": "NUMBER",
      "vol_change": "NUMBER",
      "vol_pct": "STRING",
      "TLPFee": "NUMBER",
      "TLPFee_change": "NUMBER",
      "TLPFee_pct": "STRING",
      "ProtocolFee": "NUMBER",
      "ProtocolFee_change": "NUMBER",
      "ProtocolFee_pct": "STRING"
    },
    "rows": [
      {
        "week_start": "2026-02-02T00:00:00Z",
        "total_vol": 61391.62,
        "daily_vol": 8770.23,
        "vol_change": 60862.21,
        "vol_pct": "11496.23%",
        "TLPFee": 47.48,
        "TLPFee_change": 47.13,
        "TLPFee_pct": "13465.71%",
        "ProtocolFee": 20.14,
        "ProtocolFee_change": 12.68,
        "ProtocolFee_pct": "169.97%"
      }
    ]
  }
}
```

---

## 手續費分配邏輯（SQL 內建）

SQL 中已定義手續費分配規則：

| 來源事件 | TLP Fee 比例 | Protocol Fee 比例 |
|---------|-------------|------------------|
| OrderFilled (realized_fee_in_usd) | 70% | 30% |
| RealizeFunding (realized_funding_fee_usd) | 100% | 0% |
| RealizeOption (fee_usd) | 70% | 30% |
| MintLp (mint_fee_usd) | 0% | 100% |
| BurnLp (burn_fee_usd) | 0% | 100% |
| Swap (fee_amount_usd) | 70% | 30% |

> TLP Fee = iTLP + mTLP 全部 TLP 用戶分到的手續費

---

## 資料特性

- **回傳行數**：通常 2-3 行（當週 + 上週 + 可能的前前週，用於計算 WoW 變化）
- **WoW 對比已內建**：SQL 已自動做好 `LEFT JOIN ... INTERVAL 7 DAY`，不需額外計算
- **首週無對比數據**：最早的一週 vol_pct / TLPFee_pct / ProtocolFee_pct 會顯示 `"-"`
- **交易量來源**：OrderFilled（一般交易）+ Liquidate（清算）

---

## 注意事項

- 此 query 使用 SQL endpoint，需要加 `User-Agent` header（否則被 Cloudflare 擋 403）
- 時間變數格式為 `toDateTime('YYYY-MM-DD HH:MM:SS', 'UTC')`，與 Query 1 的 Unix timestamp 不同
- 週報主要取 `rows[0]`（最新週）的數據即可
