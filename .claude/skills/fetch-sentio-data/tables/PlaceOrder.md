# PlaceOrder

> 下單事件。使用者提交交易訂單時觸發，包含開倉、加倉、止盈（TP）、止損（SL）以及主動關倉。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者提交任何類型的交易訂單時 |
| 關聯事件 | **PlaceOrder** → OrderFilled / CancelOrder |
| Processor Handler | `trading.onEventCreateTradingOrderEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 下單時間 | 原始事件時間 | 2026-04-02T07:52:40.771Z |
| base_token | String | — | 交易標的代幣 | `parse_token(base_token.name)` | SUI |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | SUI |
| order_type | String | — | 訂單類型（見下方說明） | 見判斷邏輯 | Limit |
| side | String | — | `Long`（做多）或 `Short`（做空） | `is_long ? "Long" : "Short"` | Long |
| status | String | — | 訂單狀態：`Filled`（市價單已成交）或 `Open`（掛單中） | `filled ? "Filled" : "Open"` | Open |
| price | Float64 | USD | 訂單價格（限價單為掛單價；市價單為成交價） | 市價單: `filled_price / 10^8`; 限價單: `trigger_price / 10^8` | 0.90726235 |
| size | Float64 | base_token | 訂單數量 | `data_decoded.size / 10^(base_token_decimal)` | 74 |
| size_usd | Float64 | USD | 訂單價值 | `size * price` | 67.1374139 |
| collateral | Float64 | collateral_token | 保證金數量（TP/SL 單為 0） | `data_decoded.collateral_amount / 10^(collateral_decimal)` | 2.3125 |
| order_id | Int64 | — | 訂單唯一識別碼 | 原始值 | 4812 |
| position_id | Int64 | — | 關聯倉位 ID（開倉時為 0，TP/SL/加倉時為既有倉位 ID） | `linked_position_id` | 0 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 下單者地址 | 0xc533c11ff... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260671041 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | trading |
| distinct_event_id | String | 事件唯一 ID | 1bfb1cf9347ba972 |
| event_name | String | 固定值 | PlaceOrder |
| log_index | Int64 | log 索引 | 2 |
| transaction_hash | String | 交易雜湊 | Ef6UWiMZ6y... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## order_type 判斷邏輯

| order_type | 條件（processor.ts） | 說明 |
|-----------|---------------------|------|
| `Market` | `filled = true` | 市價單，下單即成交（status = Filled） |
| `Limit` | 非 reduce_only | 開倉或加倉的限價單（掛單等待觸價） |
| `TP` | `reduce_only && !is_stop_order` | 止盈單（Take Profit）。也用於使用者主動關倉 |
| `SL` | `reduce_only && is_stop_order` | 止損單（Stop Loss） |

### order_type 與操作的對應

| 使用者操作 | order_type | position_id | collateral |
|-----------|-----------|-------------|-----------|
| 開倉（限價） | Limit | 0 | > 0 |
| 開倉（市價） | Market | 0 | > 0 |
| 加倉 | Limit | 既有倉位 ID | > 0 |
| 設定止盈 | TP | 既有倉位 ID | 0 |
| 設定止損 | SL | 既有倉位 ID | 0 |
| 主動關倉 | TP | 既有倉位 ID | 0 |

---

## 常見查詢模式

### 統計下單次數（按類型）

```sql
SELECT
    order_type,
    count(*) AS order_count
FROM PlaceOrder
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY order_type
```

### 查詢特定地址的下單記錄

```sql
SELECT timestamp, base_token, order_type, side, status, price, size, size_usd
FROM PlaceOrder
WHERE distinct_id = '0x目標地址'
ORDER BY timestamp DESC
```

### 與 OrderFilled 關聯（追蹤訂單從下單到成交）

```sql
-- 用 order_id 關聯
SELECT p.timestamp AS place_time, o.timestamp AS fill_time,
       p.order_type, p.price AS order_price, o.filled_price
FROM PlaceOrder p
JOIN OrderFilled o ON p.order_id = o.order_id
WHERE p.distinct_id = '0x目標地址'
```

---

## 注意事項

- **position_id = 0**：代表開倉（倉位尚未存在）。注意 0 表示「不存在」，理論上可能有既有倉位的 position_id 也是 0 而造成誤 match，因此**跨表關聯時應優先使用 order_id**
- **order_id 的唯一性**：order_id 在每個 base_token 內獨立排序。也就是說 ETH 的 order_id = 10 和 BTC 的 order_id = 10 是不同的訂單。**跨表關聯時必須同時對齊 base_token + order_id**
- `collateral = 0` 通常代表 TP/SL 單（不需要額外保證金）
- `status`：目前一般都是 `"Open"`（掛單中）。舊資料可能出現 `"Filled"`（早期版本的市價單）
- **判斷市價單**：可將 PlaceOrder 與同一 order_id + base_token 的 OrderFilled 配對，若兩者時間非常接近（幾秒內），即可推斷為市價單
- `price` 的含義依 order_type 不同：限價單 = 掛單觸發價，TP/SL = 目標價格
- 使用者主動關倉的 order_type 也是 `TP`，與設定止盈單相同，需透過上下文區分

---

*建立於 2026-04-02，基於 processor.ts `trading.onEventCreateTradingOrderEvent` 和 API 樣本資料。*
