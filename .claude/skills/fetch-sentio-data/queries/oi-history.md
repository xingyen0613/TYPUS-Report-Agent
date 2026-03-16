# Query 10: OI History（OI 歷史變化）

**用途**：獲取每小時各交易對的 Open Interest（OI）歷史變化，用於追蹤週內 OI 趨勢、WoW 比較、以及各幣種 OI 消長。

**API Endpoint**：`https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute`（SQL endpoint）

**特性**：此查詢計算從協議啟動以來的累積 OI，透過 Sentio `variables` 中的 `startTime/endTime` 控制輸出的時間範圍。每小時一筆數據，並對無交易時段做向前填補（Forward Fill）。

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

使用直接 SQL 字串替換（同 Query 5、6），在 Python 中替換 SQL 裡的 `{{START_TIME}}` 和 `{{END_TIME}}`：
```python
sql = sql.replace("{{START_TIME}}", sql_start)
sql = sql.replace("{{END_TIME}}", sql_end)
# payload 中的 variables 欄位不需設定
```

這樣可確保：
1. `event` CTE 只讀取目標週結束前的事件（避免 range_bounds 延伸到執行當下）
2. 最終輸出只包含目標週的小時數據（不多不少）

> `size: 10000` 以容納一週 168 小時 × 多筆數據。

### 完整 SQL

```sql
-- OI history
WITH
event as (
    SELECT
    timestamp as time,
    'OrderFilled' as event_name,
    base_token,
    position_id,
    order_id,
    case
        when order_type = 'Close' then (-1) * filled_size
        else filled_size
    end as Size,
    filled_price as price,
    null
    from `OrderFilled`
    WHERE timestamp < toDateTime('{{END_TIME}}', 'UTC')
    union ALL
    SELECT
    timestamp as time,
    'Liquidate' as event_name,
    base_token,
    position_id,
    0 as order_id,
    (-1) * position_size as Size,
    trading_price as price,
    null
    from `Liquidate`
    WHERE timestamp < toDateTime('{{END_TIME}}', 'UTC')
),
fixdata as (
    SELECT
    time,
    toStartOfHour(time) as hour,
    event_name,
    base_token,
    position_id,
    order_id,
    case
        when event_name = 'OrderFilled' and base_token = 'SUI' and order_id = 2761 then -1000
        when event_name = 'OrderFilled' and base_token = 'WAL' and order_id = 150 then -1000
        when event_name = 'OrderFilled' and base_token = 'WAL' and order_id = 164 then -20354
        when event_name = 'OrderFilled' and base_token = 'BTC' and order_id = 12498 then round(Size,4)
        else Size
    end as Size,
    price
    from event
    order by time desc
),
agg_by_hour as (
    SELECT
    hour,
    base_token,
    sum(Size) as Size,
    argMax(price, time) AS price
    from fixdata
    group by base_token, hour
    order by hour desc
),
Accum_size as (
    SELECT
    hour,
    base_token,
    round(price,6) as price,
    sum(Size) OVER (
        PARTITION BY base_token
        ORDER BY hour
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_size
    from agg_by_hour
    order by hour desc
),
open_interest_value as (
    SELECT
    hour,
    base_token,
    round(cumulative_size * price,2) as OI,
    1 AS has_data
    from Accum_size
),
range_bounds AS (
    SELECT
        min(hour) AS start_time,
        max(hour) AS end_time
    FROM open_interest_value
),
tokens AS (
    SELECT DISTINCT base_token FROM open_interest_value
),
time_range AS (
    SELECT
        range_bounds.start_time + INTERVAL number HOUR AS hour
    FROM range_bounds
    JOIN numbers(10000) AS n ON 1 = 1
    WHERE n.number <= dateDiff('hour', range_bounds.start_time, range_bounds.end_time)
),
grid AS (
    SELECT
        t.hour,
        b.base_token
    FROM time_range t
    CROSS JOIN tokens b
),
joined AS (
    SELECT
        g.hour,
        g.base_token,
        o.OI,
        if(o.has_data = 1, 1, 0) AS has_data
    FROM grid g
    LEFT JOIN open_interest_value o
    ON g.hour = o.hour AND g.base_token = o.base_token
),
filled AS (
    SELECT
        hour,
        base_token,
        OI,
        has_data,
        if(
            has_data = 1,
            OI,
            argMaxIf(OI, hour, has_data = 1) OVER (
                PARTITION BY base_token
                ORDER BY hour
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS filled_OI
    FROM joined
)
SELECT
    hour,
    sum(filled_OI) as Total,
    MAXIf(filled_OI, base_token = 'SUI') AS SUI,
    MAXIf(filled_OI, base_token = 'WAL') AS WAL,
    MAXIf(filled_OI, base_token = 'DEEP') AS DEEP,
    MAXIf(filled_OI, base_token = 'BTC') AS BTC,
    MAXIf(filled_OI, base_token = 'TYPUS') AS TYPUS,
    MAXIf(filled_OI, base_token = 'ETH') AS ETH,
    MAXIf(filled_OI, base_token = 'SPYX') AS SPYX,
    MAXIf(filled_OI, base_token = 'QQQX') AS QQQX,
    MAXIf(filled_OI, base_token = 'NVDAX') AS NVDAX,
    MAXIf(filled_OI, base_token = 'APT') AS APT,
    MAXIf(filled_OI, base_token = 'SOL') AS SOL,
    MAXIf(filled_OI, base_token = 'JPY') AS JPY,
    MAXIf(filled_OI, base_token = 'XAG') AS XAG,
    MAXIf(filled_OI, base_token = 'XRP') AS XRP,
    MAXIf(filled_OI, base_token = 'HYPE') AS HYPE,
    MAXIf(filled_OI, base_token = 'DOGE') AS DOGE,
    MAXIf(filled_OI, base_token = 'TSLAX') AS TSLAX,
    MAXIf(filled_OI, base_token = 'XAU') AS XAU,
    MAXIf(filled_OI, base_token = 'USOIL') AS USOIL,
    MAXIf(filled_OI, base_token = 'BNB') AS BNB
FROM filled
WHERE hour >= toDateTime('{{START_TIME}}', 'UTC') AND hour < toDateTime('{{END_TIME}}', 'UTC')
GROUP BY hour
ORDER BY hour desc;
```

> SQL 計算從協議啟動以來的完整累積 OI，Sentio 的 `variables` 時間範圍負責過濾最終輸出的時間窗口。

---

## SQL 邏輯說明

| CTE | 功能 |
|-----|------|
| `event` | 合併 `OrderFilled`（Open/Close）和 `Liquidate` 事件，Close 和 Liquidate 取負值 |
| `fixdata` | 修正已知異常數據（特定 order_id 的錯誤數值），按小時分箱 |
| `agg_by_hour` | 按幣種、小時匯總淨倉位變化和最新價格 |
| `Accum_size` | 對每個幣種做累積加總（running sum），得到每小時的淨持倉量 |
| `open_interest_value` | 累積持倉量 × 當時價格 = OI（USD） |
| `range_bounds` / `tokens` / `time_range` / `grid` | 建立完整的時間 × 幣種格子，確保每小時每幣種都有數據 |
| `joined` / `filled` | 將 OI 數據填入格子，無數據時段用向前填補（Forward Fill） |
| 最終 SELECT | Pivot 成寬表格，每列一個小時，每欄一個幣種 |

---

## 回傳欄位

| 欄位 | 類型 | 單位 | 說明 |
|------|------|------|------|
| `hour` | TIME | — | 小時時間戳（ISO 8601） |
| `Total` | NUMBER | USD | 全平台總 OI |
| `SUI` | NUMBER | USD | SUI OI |
| `WAL` | NUMBER | USD | WAL OI |
| `DEEP` | NUMBER | USD | DEEP OI |
| `BTC` | NUMBER | USD | BTC OI |
| `TYPUS` | NUMBER | USD | TYPUS OI |
| `ETH` | NUMBER | USD | ETH OI |
| `SPYX` | NUMBER | USD | SPYX OI |
| `QQQX` | NUMBER | USD | QQQX OI |
| `NVDAX` | NUMBER | USD | NVDAX OI |
| `APT` | NUMBER | USD | APT OI |
| `SOL` | NUMBER | USD | SOL OI |
| `JPY` | NUMBER | USD | JPY OI |
| `XAG` | NUMBER | USD | XAG OI |
| `XRP` | NUMBER | USD | XRP OI（歷史存量） |
| `HYPE` | NUMBER | USD | HYPE OI（歷史存量） |
| `DOGE` | NUMBER | USD | DOGE OI（歷史存量） |
| `TSLAX` | NUMBER | USD | TSLAX OI |
| `XAU` | NUMBER | USD | XAU OI |
| `USOIL` | NUMBER | USD | USOIL OI |
| `BNB` | NUMBER | USD | BNB OI |

> 如果某幣種在該時段無 OI，值為 null 或 0。新增交易對時需在 SQL 的最終 SELECT 中加入對應 `MAXIf` 欄位。

---

## 範例回應

```json
{
  "result": {
    "columns": ["hour", "Total", "BTC", "ETH", "SOL", "SUI", "DEEP", "WAL", "APT", "XRP", "HYPE", "DOGE"],
    "columnTypes": {
      "hour": "TIME",
      "Total": "NUMBER",
      "BTC": "NUMBER",
      "ETH": "NUMBER",
      "SOL": "NUMBER",
      "SUI": "NUMBER",
      "DEEP": "NUMBER",
      "WAL": "NUMBER",
      "APT": "NUMBER",
      "XRP": "NUMBER",
      "HYPE": "NUMBER",
      "DOGE": "NUMBER"
    },
    "rows": [
      {
        "hour": "2026-02-08T23:00:00Z",
        "Total": 12580.45,
        "BTC": 540.20,
        "ETH": 0,
        "SOL": 0,
        "SUI": 11540.25,
        "DEEP": 0,
        "WAL": 300.00,
        "APT": 0,
        "XRP": 0,
        "HYPE": 200.00,
        "DOGE": 0
      },
      {
        "hour": "2026-02-08T22:00:00Z",
        "Total": 12450.30,
        "BTC": 540.20,
        "ETH": 0,
        "SOL": 0,
        "SUI": 11410.10,
        "DEEP": 0,
        "WAL": 300.00,
        "APT": 0,
        "XRP": 0,
        "HYPE": 200.00,
        "DOGE": 0
      }
    ]
  }
}
```

---

## 資料特性

- **回傳行數**：每小時一列，一週 ≈ 168 列（按 `hour desc` 排序）
- **累積式計算**：OI 是 running sum，不是增量。每列的值是該小時的「存量」
- **向前填補**：無交易事件的時段，OI 繼承上一小時的值（Forward Fill）
- **異常數據修正**：SQL 中已內建 4 筆已知異常 order 的修正邏輯
- **幣種欄位固定**：目前 Pivot 寫死 11 個幣種。新增交易對時需更新 SQL
- **單位**：USD（已乘以當時價格）

---

## 在週報中的用途

- **OI 趨勢分析**：週初 vs 週末 OI 變化，判斷市場槓桿擴張或收縮
- **WoW OI 比較**：與上週末 OI 對比（需搭配歷史數據）
- **幣種 OI 消長**：哪些幣種的 OI 在增長/縮減
- **週內峰谷**：標記 OI 峰值和谷值，關聯市場事件
- **情緒佐證**：OI 擴張通常代表信心增長，OI 收縮代表去槓桿
- **圖表數據源**：提供 OI 走勢圖的原始數據
