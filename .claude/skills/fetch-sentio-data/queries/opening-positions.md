# Query 8: Opening Positions（當前持倉狀況）

**用途**：獲取當前各交易對的持倉快照，包含總持倉量、多空分布、淨曝險、Long/Short Ratio、未實現盈虧（交易者視角與 TLP 視角）。

**API Endpoint**：`https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute`（SQL endpoint）

**特性**：這是即時快照查詢，不依賴時間範圍（SQL 中無 WHERE 時間過濾），反映的是**當下**的持倉狀態。

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

> 注意：雖然 variables 中有 startTime/endTime，但此 SQL 不使用時間過濾，查詢的是當下所有未平倉部位。

### 完整 SQL

```sql
-- opening position (no include OpenTradingFee)
WITH
price as (
    SELECT
        CASE 
            WHEN UPPER(symbol) = 'XAUT' THEN 'XAU'
            WHEN UPPER(symbol) = 'JPYC' THEN 'JPY'
            WHEN UPPER(symbol) = 'XAGM' THEN 'XAG'
            WHEN UPPER(symbol) = 'WOIL' THEN 'USOIL'
            ELSE UPPER(symbol)
        END AS symbol,
        argMax(
        CASE
            WHEN UPPER(symbol) = 'JPY' THEN 1 / price
            ELSE price
        END,
        time
    ) AS latest_price,
        max(time) AS latest_time
    FROM `token.prices`
    GROUP BY symbol
),
openfilled as (
    SELECT
    OrderFilled.timestamp,
    OrderFilled.order_id,
    OrderFilled.position_id,
    OrderFilled.side,
    OrderFilled.filled_size,
    OrderFilled.base_token,
    OrderFilled.filled_price,
    OrderFilled.distinct_id,
    OrderFilled.transaction_hash
    from `OrderFilled`
    where OrderFilled.order_type = 'Open'
),
closefilled as (
    SELECT
    OrderFilled.position_id,
    sum(OrderFilled.filled_size) as filled_size,
    OrderFilled.base_token
    from `OrderFilled`
    where OrderFilled.order_type = 'Close'
    group by base_token, position_id
),
liquidate as (
    SELECT
    Liquidate.position_id,
    Liquidate.position_size,
    Liquidate.base_token
    from `Liquidate`
),
remainsize as (
    select
    openfilled.timestamp,
    openfilled.order_id as order_id,
    openfilled.position_id as position_id,
    openfilled.side,
    openfilled.filled_size - closefilled.filled_size - liquidate.position_size as remain_size,
    openfilled.base_token as base_token,
    openfilled.filled_price,
    openfilled.distinct_id,
    openfilled.transaction_hash
    from openfilled
    left join closefilled on closefilled.base_token = openfilled.base_token and closefilled.position_id = openfilled.position_id
    left join liquidate on liquidate.base_token = openfilled.base_token and liquidate.position_id = openfilled.position_id
),
openingposition as (
    SELECT
    remainsize.timestamp as entrytime,
    remainsize.order_id,
    remainsize.position_id as position_id,
    remainsize.side as side,
    remainsize.remain_size,
    remainsize.base_token as token,
    price.latest_price as last_price,
    remainsize.remain_size * price.latest_price as Current_position_value,
    remainsize.filled_price as filled_price,
    price.latest_price as latest_price,
    CASE
        WHEN remainsize.side = 'Short' THEN (latest_price - filled_price) * remain_size * (-1)
        ELSE (latest_price - filled_price) * remain_size
    END AS PnlUSD,
    COALESCE(nullif(PlaceOrder.collateral, 0), PlaceOrderWithBidReceipt.collateral) as collateral_amount,
    multiIf(
        PlaceOrder.collateral != 0, PlaceOrder.collateral_token,
        PlaceOrderWithBidReceipt.collateral_token
    ) AS collateral_token,
    price.latest_time as latest_price_update,
    remainsize.distinct_id,
    remainsize.transaction_hash
    from remainsize
    left join price on price.symbol = remainsize.base_token
    left join `PlaceOrder` ON PlaceOrder.base_token = remainsize.base_token and PlaceOrder.order_id = remainsize.order_id
    left join `PlaceOrderWithBidReceipt` ON PlaceOrderWithBidReceipt.base_token = remainsize.base_token and PlaceOrderWithBidReceipt.order_id = remainsize.order_id
    where remainsize.remain_size > 0
),
total_opening_TLPpnl as (
    SELECT
    token,
    sum(PnlUSD) * (-1) as PnlUSDForTLP
    from openingposition
    group by token
),
openingpositionbypair as (
    SELECT
    sum(remain_size) as TotalSize,
    token as Token,
    avg(last_price) as LastPrice,
    sum(Current_position_value) as TotalValue,
    SUM(CASE WHEN side = 'Long' THEN Current_position_value ELSE 0 END) AS Long_Value,
    SUM(CASE WHEN side = 'Short' THEN Current_position_value ELSE 0 END) AS Short_Value,
    Long_Value - Short_Value as Net_Exposure_Side,
    case
        when Long_Value = 0 then 'NetShort'
        when Short_Value = 0 then 'NetLong'
        else toString(Long_Value / Short_Value)
    end as L_S_Ratio,
    sum(PnlUSD) as TraderPnlUSD,
    sum(PnlUSD) * (-1) as PnlUSDForTLP
    from openingposition
    group by token
)
SELECT
CAST(NULL AS Nullable(Decimal(76, 18))) AS TotalSize,
'ALL' as Token,
CAST(NULL AS Nullable(Float64)) AS LastPrice,
sum(TotalValue) as TotalValue,
sum(openingpositionbypair.Long_Value) as Long_Value,
sum(openingpositionbypair.Short_Value) as Short_Value,
sum(Net_Exposure_Side) as Net_Exposure_Side,
toString(Long_Value / Short_Value) as L_S_Ratio,
sum(TraderPnlUSD) as TraderPnlUSD,
sum(PnlUSDForTLP) as PnlUSDForTLP
from openingpositionbypair
union all
SELECT
*
from openingpositionbypair
order by TotalValue desc
;
```

---

## 回傳欄位

| 欄位 | 類型 | 單位 | 說明 | 週報指標 |
|------|------|------|------|---------|
| `TotalSize` | NUMBER | 顆數 | 該幣種的總持倉大小（原生單位）。ALL 列為 null | Position Size |
| `Token` | STRING | — | 幣種名稱，第一列固定為 `"ALL"`（全平台彙總） | — |
| `LastPrice` | NUMBER | USD | Sentio 上該幣種的最新價格。ALL 列為 null | Current Price |
| `TotalValue` | NUMBER | USD | 總開倉量（= Open Interest Value） | OI Value |
| `Long_Value` | NUMBER | USD | 多頭持倉量 | Long OI |
| `Short_Value` | NUMBER | USD | 空頭持倉量 | Short OI |
| `Net_Exposure_Side` | NUMBER | USD | LP 淨曝險 = Long - Short。正=LP 多方曝險，負=LP 空方曝險 | Net Exposure |
| `L_S_Ratio` | STRING | — | Long/Short 比率。特殊值：`"NetLong"` / `"NetShort"`（當一方為 0） | L/S Ratio |
| `TraderPnlUSD` | NUMBER | USD | 交易者未實現盈虧 | Unrealized Trader P&L |
| `PnlUSDForTLP` | NUMBER | USD | TLP 未實現盈虧（= TraderPnlUSD × -1） | Unrealized TLP P&L |

---

## 範例回應

```json
{
  "result": {
    "columns": ["TotalSize", "Token", "LastPrice", "TotalValue", "Long_Value", "Short_Value", "Net_Exposure_Side", "L_S_Ratio", "TraderPnlUSD", "PnlUSDForTLP"],
    "rows": [
      {
        "TotalSize": null, "Token": "ALL", "LastPrice": null,
        "TotalValue": 12104.71, "Long_Value": 7098.55, "Short_Value": 5006.16,
        "Net_Exposure_Side": 2092.39, "L_S_Ratio": "1.4179630889648653",
        "TraderPnlUSD": 681.47, "PnlUSDForTLP": -681.47
      },
      {
        "TotalSize": 12232, "Token": "SUI", "LastPrice": 0.9434,
        "TotalValue": 11540.32, "Long_Value": 6874.94, "Short_Value": 4665.38,
        "Net_Exposure_Side": 2209.57, "L_S_Ratio": "1.4736",
        "TraderPnlUSD": 690.25, "PnlUSDForTLP": -690.25
      },
      {
        "TotalSize": 0.039, "Token": "XAU", "LastPrice": 5025.65,
        "TotalValue": 196.00, "Long_Value": 196.00, "Short_Value": 0.00,
        "Net_Exposure_Side": 196.00, "L_S_Ratio": "NetLong",
        "TraderPnlUSD": 0.24, "PnlUSDForTLP": -0.24
      }
    ]
  }
}
```

---

## 資料特性

- **第一列固定為 `ALL`**：全平台彙總，TotalSize 和 LastPrice 為 null
- **後續列按 TotalValue 降序排列**：最大持倉的交易對排最前
- **即時快照**：反映查詢當下的持倉狀態，不是歷史數據
- **幣種動態**：會隨實際有持倉的交易對變化
- **L_S_Ratio 特殊值**：當 Long 或 Short 為 0 時，回傳 `"NetLong"` 或 `"NetShort"` 字串
- **TLP P&L = Trader P&L × (-1)**：LP 作為交易者對手方

---

## 在週報中的用途

- **Open Interest 概覽**：全平台總 OI、各交易對 OI 排名
- **多空分布分析**：L/S Ratio、Net Exposure 方向
- **LP 風險評估**：LP 當前曝險方向與未實現盈虧
- **交易對熱度**：哪些幣種 OI 最大
