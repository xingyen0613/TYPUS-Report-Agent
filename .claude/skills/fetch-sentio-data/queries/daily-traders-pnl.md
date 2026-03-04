# Query 5: Daily Traders P&L（每日交易者盈虧）

**用途**：獲取每日所有交易者的淨盈虧（USD），用於了解整體交易者損益狀況。正值代表交易者整體獲利，負值代表虧損（= TLP 獲利）。

**API Endpoint**：`https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute`（SQL endpoint）

---

## 請求 Payload

```json
{
  "version": 9,
  "sqlQuery": {
    "sql": "<SQL_CONTENT>",
    "variables": {
      "startTime": "toDateTime('<START>', 'UTC')",
      "endTime": "toDateTime('<END>', 'UTC')"
    },
    "size": 10000
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

此 query 的時間過濾是**直接寫在 SQL WHERE 子句中**，格式為：
```sql
where day >= toDateTime('2026-02-02 08:00:00', 'UTC') and day < toDateTime('2026-02-09 08:00:00', 'UTC')
```

> 注意：`variables` 中的 startTime/endTime 未被 SQL 引用，實際時間需直接替換 SQL 字串中的日期值。SKILL.md 執行時需做字串替換。

### 完整 SQL

```sql
WITH
TraderPnl_history as (
    SELECT
    toDate(timestamp) as day,
    base_token as token,
    CAST( realized_pnl AS Float64 ) as Pnl
    from OrderFilled
    UNION ALL
    SELECT
    toDate(timestamp) as day,
    base_token as token,
    CAST((value_for_lp_pool_usd + liquidator_fee_usd)AS Float64) * (-1) as Pnl
    from Liquidate
    UNION ALL
    SELECT
    toDate(timestamp) as day,
    base_token as token,
    CAST(realized_funding_fee_usd AS Float64) * (-1) as Pnl
    from `RealizeFunding`
    UNION ALL
    SELECT
    toDate(timestamp) as day,
    base_token as token,
    CAST(
        if(
            user_remaining_value = 0 OR user_remaining_value IS NULL,
            0,
            user_remaining_in_usd +
            (realized_loss_value - exercise_balance_value) * (user_remaining_in_usd / user_remaining_value)
        ) AS Float64
    ) AS Pnl
    from `RealizeOption`
),
DailyPnl as (
    SELECT
        day,
        sum(Pnl) as Daily_PnlUSD
    FROM TraderPnl_history
    GROUP BY day
)
SELECT *
FROM DailyPnl
where day >= toDateTime('{{START_TIME}}', 'UTC') and day < toDateTime('{{END_TIME}}', 'UTC')
;
```

> `{{START_TIME}}` 和 `{{END_TIME}}` 為佔位符，SKILL.md 執行時替換為實際日期，格式：`YYYY-MM-DD HH:MM:SS`

---

## 回傳欄位

| 欄位 | 類型 | 單位 | 說明 | 週報指標 |
|------|------|------|------|---------|
| `day` | TIME | — | 日期（ISO 8601） | 日期 |
| `Daily_PnlUSD` | NUMBER | USD | 當日所有交易者淨 P&L | Daily Traders P&L |

---

## 範例回應

```json
{
  "result": {
    "columns": ["day", "Daily_PnlUSD"],
    "columnTypes": {
      "day": "TIME",
      "Daily_PnlUSD": "NUMBER"
    },
    "rows": [
      { "day": "2026-02-03T00:00:00Z", "Daily_PnlUSD": -4.05 },
      { "day": "2026-02-04T00:00:00Z", "Daily_PnlUSD": -4.71 },
      { "day": "2026-02-05T00:00:00Z", "Daily_PnlUSD": -364.56 },
      { "day": "2026-02-06T00:00:00Z", "Daily_PnlUSD": -98.06 },
      { "day": "2026-02-07T00:00:00Z", "Daily_PnlUSD": 2.64 },
      { "day": "2026-02-08T00:00:00Z", "Daily_PnlUSD": 6.46 },
      { "day": "2026-02-09T00:00:00Z", "Daily_PnlUSD": 26.34 }
    ]
  }
}
```

---

## P&L 計算邏輯（SQL 內建）

| 來源事件 | P&L 計算方式 | 說明 |
|---------|-------------|------|
| OrderFilled | `realized_pnl + realized_fee_in_usd * 0.3` | 交易實現盈虧 + 30% 手續費回饋 |
| Liquidate | `value_for_lp_pool_usd * (-1)` | 清算損失（取反為交易者視角） |
| RealizeFunding | `realized_funding_fee_usd * (-1)` | 資金費用（取反為交易者視角） |
| RealizeOption | 條件計算（見 SQL） | 期權結算，含剩餘價值與實現損失 |

> **正值** = 交易者整體獲利（TLP 虧損）
> **負值** = 交易者整體虧損（TLP 獲利）

---

## 資料特性

- **回傳行數**：每天一列，7 天 = 7 列
- **數值含義**：負值對 TLP 有利（交易者虧損 = TLP 賺到的）
- **單位**：USD

---

## 在週報中的用途

- 每日 P&L 走勢，觀察交易者整體表現
- 計算週總 P&L（加總 7 天）
- 反向解讀：交易者虧損 = TLP 用戶收益
