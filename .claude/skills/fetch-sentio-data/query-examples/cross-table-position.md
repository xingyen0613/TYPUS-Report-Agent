# 範例：追蹤倉位完整歷史（跨表）

> 展示如何用 position_id 跨表查詢一個倉位從開倉到平倉/清算的完整歷史。

## 使用到的 Table
- `OrderFilled`（開倉 / 平倉 / 加倉）
- `RealizeFunding`（持倉期間資金費結算）
- `Liquidate`（若被清算）

## 需求
「查 position_id = 2112 的 SUI 倉位完整歷史」

## SQL

```sql
-- 用 UNION ALL 合併三張表的事件，按時間排序
-- 關聯鍵：position_id + base_token（見 _EVENT-FLOW.md）

WITH position_history AS (
    -- 開倉 / 平倉 / 加倉事件
    SELECT
        timestamp,
        'OrderFilled' AS event,
        order_type AS action,            -- Open / Close / Increase
        side,
        filled_price AS price,
        filled_size AS size,
        round(filled_price * filled_size, 2) AS value_usd,
        round(realized_pnl, 4) AS pnl_usd,
        round(realized_fee_in_usd, 4) AS fee_usd
    FROM OrderFilled
    WHERE position_id = 2112 AND base_token = 'SUI'

    UNION ALL

    -- 資金費結算事件
    SELECT
        timestamp,
        'RealizeFunding' AS event,
        'Funding' AS action,
        '' AS side,
        0 AS price,
        0 AS size,
        0 AS value_usd,
        round(CAST(realized_funding_fee_usd AS Float64) * (-1), 4) AS pnl_usd,  -- 取反為交易者視角
        0 AS fee_usd
    FROM RealizeFunding
    WHERE position_id = 2112 AND base_token = 'SUI'

    UNION ALL

    -- 清算事件
    SELECT
        timestamp,
        'Liquidate' AS event,
        'Liquidated' AS action,
        '' AS side,
        trading_price AS price,
        position_size AS size,
        round(position_size * trading_price, 2) AS value_usd,
        round(CAST((value_for_lp_pool_usd + liquidator_fee_usd) AS Float64) * (-1), 4) AS pnl_usd,
        round(CAST(liquidator_fee_usd AS Float64), 4) AS fee_usd
    FROM Liquidate
    WHERE position_id = 2112 AND base_token = 'SUI'
)

SELECT * FROM position_history
ORDER BY timestamp ASC
```

## 學到的模式
1. **跨表關聯鍵**：`base_token` + `position_id` 可追蹤同一倉位在不同事件中的記錄（注意：必須先對齊 base_token，因為 order_id 和 position_id 在每個 base_token 內獨立排序）
2. **UNION ALL 合併事件**：用統一的欄位結構合併不同表，方便時間排序
3. **Sign Convention**：
   - OrderFilled 的 `realized_pnl` 已是交易者視角（正 = 獲利）
   - RealizeFunding 的 `realized_funding_fee_usd` 需乘以 `-1`（正值 = 交易者付出 → 轉為負值）
   - Liquidate 的 `value_for_lp_pool_usd + liquidator_fee_usd` 需乘以 `-1`（LP 獲得 → 交易者損失）
4. 一個倉位的生命週期：Open → (Funding × N) → Close 或 Liquidate
