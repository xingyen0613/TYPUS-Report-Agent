# 範例：上週被清算最多的地址

> 展示如何跨表查詢清算事件，找出清算金額最大的交易者。

## 使用到的 Table
- `Liquidate`（主表）

## 需求
「上週被清算金額最高的前 10 個地址」

## SQL

```sql
-- 來源表：Liquidate（見 tables/Liquidate.md）
-- 關鍵欄位：distinct_id（被清算者）、position_size、trading_price
-- 排除刷量地址（見 _QUERY-WRITING-GUIDE.md）
SELECT
    distinct_id AS trader,
    count(*) AS liquidation_count,
    round(sum(position_size * trading_price), 2) AS total_liquidation_usd,
    groupArray(base_token) AS tokens
FROM Liquidate
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
  AND distinct_id NOT IN (
      '0x5db51fb378d12be4b6b79b7b23e86e920f8b7cbbfe82b394de65b243b09f2953',
      '0x57728a38a68e921d990d40ae5cfddf3a7b09599577ef006c9678cc84b4cc9cce',
      '0xb2c42812f18d448248adf2b65970a3f8dbe0d471a8cdd0e915857e3b2e5f90f5'
  )
GROUP BY trader
ORDER BY total_liquidation_usd DESC
LIMIT 10
```

## 學到的模式
1. Liquidate 的交易量計算：`position_size * trading_price`（與 OrderFilled 不同，用 position_size 而非 filled_size）
2. 務必排除已知刷量地址
3. `groupArray()` 是 ClickHouse 特有函數，可以聚合成陣列
4. `distinct_id` 在 Liquidate 中代表被清算者（= `data_decoded.user`）
