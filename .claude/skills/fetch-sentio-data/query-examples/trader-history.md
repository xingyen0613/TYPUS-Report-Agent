# 範例：查詢特定地址的交易記錄

> 展示如何查詢單一交易者的所有成交記錄，包含開倉和平倉。

## 使用到的 Table
- `OrderFilled`（主表）

## 需求
「查 0xABC... 上週的所有交易記錄和盈虧」

## SQL

```sql
-- 來源表：OrderFilled（見 tables/OrderFilled.md）
-- 關鍵欄位：distinct_id（交易者地址）、order_type、filled_price、filled_size
SELECT
    timestamp,
    base_token,
    order_type,                               -- 'Open' / 'Close' / 'Increase'
    side,                                     -- 'Long' / 'Short'
    filled_price,
    filled_size,
    round(filled_price * filled_size, 2) AS vol_usd,  -- 交易量 = 價格 × 數量
    round(realized_pnl, 4) AS realized_pnl,           -- 僅 Close 有意義
    round(realized_fee_in_usd, 4) AS fee_usd
FROM OrderFilled
WHERE distinct_id = '0xABC...'
  AND timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
ORDER BY timestamp DESC
```

## 學到的模式
1. 用 `distinct_id` 篩選交易者地址
2. `filled_price * filled_size` 是計算交易量的標準公式
3. 時間篩選使用 `toDateTime` + 半開區間（`>=` 和 `<`）
4. `realized_pnl` 對 Open 事件沒有意義（通常等於 -fee）
