# CancelOrder

> 取消訂單事件。使用者主動取消掛單，或系統（cranker）自動取消 TP/SL 單（例如倉位已被平倉或清算時）。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者取消掛單，或系統自動取消關聯的 TP/SL 單 |
| 關聯事件 | PlaceOrder → **CancelOrder**（或 PlaceOrder → OrderFilled） |
| Processor Handler | `trading.onEventCancelTradingOrderEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 取消時間 | 原始事件時間 | 2026-04-02T10:06:14.261Z |
| base_token | String | — | 交易標的代幣 | `parse_token(base_token.name)` | SPYX |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | USDC |
| order_id | Int64 | — | 被取消的訂單 ID | 原始值 | 48 |
| is_cranker | Int64 | — | 是否由系統自動取消（1 = cranker, 0 = 使用者） | `event.sender != event.data_decoded.user` | 1 |
| released_collateral_amount | Float64 | collateral_token | 釋放的保證金數量 | `data_decoded.released_collateral_amount / 10^(collateral_token_decimal)` | 4.205978 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 訂單擁有者地址（非 sender） | 0xa59783c9... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260701856 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | trading |
| distinct_event_id | String | 事件唯一 ID | 6da4b1058b506673 |
| event_name | String | 固定值 | CancelOrder |
| log_index | Int64 | log 索引 | 10 |
| transaction_hash | String | 交易雜湊 | FLzsd6ZZxD... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日取消訂單數（區分使用者 vs cranker）

```sql
SELECT
    toDate(timestamp) AS day,
    sumIf(1, is_cranker = 0) AS user_cancel,
    sumIf(1, is_cranker = 1) AS cranker_cancel
FROM CancelOrder
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 與 PlaceOrder 關聯（追蹤訂單從下單到取消）

```sql
SELECT
    p.timestamp AS place_time,
    c.timestamp AS cancel_time,
    p.base_token,
    p.order_type,
    p.side,
    p.size_usd,
    c.is_cranker,
    c.released_collateral_amount
FROM PlaceOrder p
JOIN CancelOrder c
    ON p.base_token = c.base_token
    AND p.order_id = c.order_id
ORDER BY c.timestamp DESC
LIMIT 20
```

---

## 注意事項

- **is_cranker = 1 且 released_collateral_amount = 0**：通常是系統取消 TP/SL 單（TP/SL 本身沒有保證金）
- **is_cranker = 0 且 released_collateral_amount > 0**：使用者主動取消限價開倉/加倉單，保證金退回
- **order_id 唯一性**：order_id 在每個 base_token 內獨立排序，跨表關聯必須同時對齊 `base_token + order_id`
- **distinct_id 是訂單擁有者**（`event.data_decoded.user`），不是交易發送者（sender）。當 cranker 代為取消時，sender ≠ distinct_id
- CancelOrder 不涉及手續費

---

*建立於 2026-04-02，基於 processor.ts `trading.onEventCancelTradingOrderEvent` 和 API 樣本資料。*
