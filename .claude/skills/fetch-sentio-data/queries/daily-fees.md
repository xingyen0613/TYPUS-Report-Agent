# Query 13: Daily Fees（每日手續費）

**用途**：獲取目標週每日的 TLP Fee 與 Protocol Fee 明細，供「Fee Breakdown」圖表製作使用。

**API Endpoint**：`https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute`
> 注意：此 query 使用 **SQL endpoint**，engine = `DEFAULT`。

---

## 請求 Payload

```json
{
  "version": 9,
  "sqlQuery": {
    "sql": "<SQL_CONTENT>",
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

### 完整 SQL（時間使用字串替換 `{{START_TIME}}` / `{{END_TIME}}`）

```sql
WITH merged_fee AS (
  SELECT
    timestamp AS time,
    toDecimal64(realized_fee_in_usd * 0.7, 8) AS TLPFee,
    toDecimal64(realized_fee_in_usd * 0.3, 8) AS ProtocolFee
  FROM OrderFilled
  WHERE timestamp >= '{{START_TIME}}' AND timestamp < '{{END_TIME}}'
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(realized_funding_fee_usd, 8) AS TLPFee,
    toDecimal64(0, 8) AS ProtocolFee
  FROM RealizeFunding
  WHERE timestamp >= '{{START_TIME}}' AND timestamp < '{{END_TIME}}'
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(fee_usd * 0.7, 8) AS TLPFee,
    toDecimal64(fee_usd * 0.3, 8) AS ProtocolFee
  FROM RealizeOption
  WHERE timestamp >= '{{START_TIME}}' AND timestamp < '{{END_TIME}}'
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(0, 8) AS TLPFee,
    toDecimal64(mint_fee_usd, 8) AS ProtocolFee
  FROM MintLp
  WHERE timestamp >= '{{START_TIME}}' AND timestamp < '{{END_TIME}}'
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(0, 8) AS TLPFee,
    toDecimal64(burn_fee_usd, 8) AS ProtocolFee
  FROM BurnLp
  WHERE timestamp >= '{{START_TIME}}' AND timestamp < '{{END_TIME}}'
  UNION ALL
  SELECT
    timestamp,
    toDecimal64(fee_amount_usd * 0.7, 8) AS TLPFee,
    toDecimal64(fee_amount_usd * 0.3, 8) AS ProtocolFee
  FROM Swap
  WHERE timestamp >= '{{START_TIME}}' AND timestamp < '{{END_TIME}}'
)

SELECT
  toDate(time) AS date,
  round(sum(TLPFee), 2) AS TLPFee,
  round(sum(ProtocolFee), 2) AS ProtocolFee
FROM merged_fee
GROUP BY date
ORDER BY date ASC
```

---

## 時間替換規則

使用 SQL 字串替換（同 Q5 / Q6 / Q10）：

```python
sql = sql.replace("{{START_TIME}}", sql_start)   # e.g. "2026-02-23 00:00:00"
sql = sql.replace("{{END_TIME}}", sql_end)         # e.g. "2026-03-02 00:00:00"
```

---

## 回傳欄位

| 欄位 | 類型 | 單位 | 說明 |
|------|------|------|------|
| `date` | DATE | — | 日期（YYYY-MM-DD） |
| `TLPFee` | NUMBER | USD | 當日 TLP 手續費（LP 分潤） |
| `ProtocolFee` | NUMBER | USD | 當日 Protocol 手續費（平台收入） |

---

## 回傳結構（範例）

```json
{
  "result": {
    "columns": ["date", "TLPFee", "ProtocolFee"],
    "rows": [
      { "date": "2026-02-23", "TLPFee": 58.40, "ProtocolFee": 28.12 },
      { "date": "2026-02-24", "TLPFee": 94.21, "ProtocolFee": 45.38 },
      { "date": "2026-02-25", "TLPFee": 112.33, "ProtocolFee": 54.06 },
      { "date": "2026-02-26", "TLPFee": 88.77, "ProtocolFee": 42.72 },
      { "date": "2026-02-27", "TLPFee": 76.54, "ProtocolFee": 36.84 },
      { "date": "2026-02-28", "TLPFee": 62.18, "ProtocolFee": 29.93 },
      { "date": "2026-03-01", "TLPFee": 25.24, "ProtocolFee": 11.81 }
    ]
  }
}
```

---

## 資料特性

- **回傳行數**：7 行（Mon–Sun），若某日無交易則不出現該行
- **手續費分配邏輯**：與 Q2 相同（OrderFilled 70/30、RealizeFunding 100/0 等）
- **與 Q2 的關係**：Q2 聚合成週總計；Q13 按日細分（兩者數字加總應相符）
