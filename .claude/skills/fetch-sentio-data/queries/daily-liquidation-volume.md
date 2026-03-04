# Query 6: Daily Liquidation Volume（每日清算量）

**用途**：獲取每日被清算的交易量（USD），搭配 Query 5（Daily Traders P&L）一起看，分析交易者損失是否主要來自清算。

**API Endpoint**：`https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute`（SQL endpoint）

**Engine**：`"LITE"`（注意：與其他 SQL query 的 `"DEFAULT"` 不同）

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
    "size": 100
  },
  "source": "DASHBOARD",
  "cachePolicy": {
    "noCache": false,
    "cacheTtlSecs": 43200,
    "cacheRefreshTtlSecs": 1800
  },
  "engine": "LITE"
}
```

### 時間參數格式

同 Query 5，時間**直接寫在 SQL WHERE 子句中**：
```sql
where date >= toDateTime('2026-02-02 08:00:00', 'UTC') and date < toDateTime('2026-02-09 08:00:00', 'UTC')
```

### 完整 SQL

```sql
WITH
vol_history AS (
    SELECT
        timestamp AS time,
        base_token AS token,
        position_size * trading_price AS vol
    FROM `Liquidate`
    -- 排除刷量地址
    WHERE distinct_id NOT IN (
        '0x5db51fb378d12be4b6b79b7b23e86e920f8b7cbbfe82b394de65b243b09f2953',
        '0x57728a38a68e921d990d40ae5cfddf3a7b09599577ef006c9678cc84b4cc9cce',
        '0xb2c42812f18d448248adf2b65970a3f8dbe0d471a8cdd0e915857e3b2e5f90f5'
    )
),
date AS (
    SELECT
        toStartOfDay(time) AS date
    FROM vol_history
    GROUP BY date
),
full_grid AS (
    SELECT date.date FROM date
),
vol_agg AS (
    SELECT
        toStartOfDay(time) AS date,
        sum(vol) AS vol
    FROM vol_history
    GROUP BY date
),
vol_filled AS (
    SELECT
        full_grid.date,
        COALESCE(vol_agg.vol, 0) AS vol
    FROM full_grid
    LEFT JOIN vol_agg ON full_grid.date = vol_agg.date
),
vol_cumulative AS (
    SELECT
        date,
        SUM(vol) OVER (ORDER BY date ASC) AS cumulative_vol
    FROM vol_filled
)
SELECT *
FROM vol_filled
WHERE date >= toDateTime('{{START_TIME}}', 'UTC') AND date < toDateTime('{{END_TIME}}', 'UTC')
;
```

> `{{START_TIME}}` / `{{END_TIME}}` 為佔位符，格式：`YYYY-MM-DD HH:MM:SS`

### 排除的刷量地址

SQL 中排除了 3 個已知刷量地址：
```
0x5db51fb378d12be4b6b79b7b23e86e920f8b7cbbfe82b394de65b243b09f2953
0x57728a38a68e921d990d40ae5cfddf3a7b09599577ef006c9678cc84b4cc9cce
0xb2c42812f18d448248adf2b65970a3f8dbe0d471a8cdd0e915857e3b2e5f90f5
```

---

## 回傳欄位

| 欄位 | 類型 | 單位 | 說明 | 週報指標 |
|------|------|------|------|---------|
| `date` | TIME | — | 日期（ISO 8601） | 日期 |
| `vol` | NUMBER | USD | 當日清算量 | Daily Liquidation Volume |

---

## 範例回應

```json
{
  "result": {
    "columns": ["date", "vol"],
    "columnTypes": { "date": "TIME", "vol": "NUMBER" },
    "rows": [
      { "date": "2026-02-03T00:00:00Z", "vol": 20.18 },
      { "date": "2026-02-04T00:00:00Z", "vol": 44.52 },
      { "date": "2026-02-05T00:00:00Z", "vol": 256.04 },
      { "date": "2026-02-06T00:00:00Z", "vol": 112.81 },
      { "date": "2026-02-07T00:00:00Z", "vol": 141.41 },
      { "date": "2026-02-09T00:00:00Z", "vol": 95.22 }
    ]
  }
}
```

---

## 資料特性

- **回傳行數**：有清算事件的天數（無清算的日期不會出現，如 2/8 無數據）
- **無清算日缺失**：如果某天沒有清算事件，該日不會出現在結果中（非 0，而是整列缺失）
- **engine**：使用 `"LITE"` 而非 `"DEFAULT"`
- **單位**：USD

---

## 在週報中的用途

- 與 Query 5（Daily Traders P&L）並排對比
- 分析交易者虧損主因：若清算量佔 P&L 虧損的大部分 → 清算是主要損失來源
- 計算週總清算量
- 週報敘事：「本週清算集中在 X 日，主因為 Y 幣種劇烈波動」
