# OrderFilled

> 訂單成交事件。每當交易者的限價單或市價單被撮合成交時觸發，包含開倉（Open）、加倉（Increase）和平倉（Close）三種類型。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 訂單被撮合成交時（含開倉、加倉、平倉） |
| 關聯事件 | PlaceOrder → **OrderFilled** → RealizeFunding / Liquidate / RemovePosition |
| Processor Handler | `position.onEventOrderFilledEvent` |

---

## 欄位說明

### 核心交易欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 事件發生時間 | 原始事件時間 | 2026-04-02T05:07:51.834Z |
| order_type | String | — | `Open`（開倉）、`Increase`（加倉）、`Close`（平倉） | Open: `linked_position_id == undefined`; Increase: `position_size > filled_size`; 其他: Close | Open |
| side | String | — | `Long`（做多）或 `Short`（做空） | `position_side ? "Long" : "Short"` | Long |
| base_token | String | — | 交易標的代幣 | `parse_token(symbol.base_token.name)` | SUI |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | SUI |
| filled_price | Float64 | USD | 成交價格 | `data_decoded.filled_price / 10^8 (PRICE_DECIMAL)` | 0.85701585 |
| filled_size | Float64 | base_token | 成交數量（以 base_token 計） | `data_decoded.filled_size / 10^(token_decimal)` | 74 |
| order_id | Int64 | — | 訂單唯一識別碼 | 原始值 | 4736 |
| position_id | Int64 | — | 倉位唯一識別碼（同一倉位可有多筆成交） | Open: `new_position_id`; Close/Increase: `linked_position_id` | 2112 |

### 費用欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯 | 範例值 |
|----------|---------|------|------|---------|--------|
| realized_trading_fee | Float64 | collateral_token | 交易手續費（以 collateral_token 計） | `data_decoded.realized_trading_fee / 10^(collateral_decimal)` | 0.074665999 |
| realized_borrow_fee | Float64 | collateral_token | 借貸費用（以 collateral_token 計） | `data_decoded.realized_borrow_fee / 10^(collateral_decimal)` | 0 |
| realized_fee | Float64 | collateral_token | 總手續費 = trading_fee + borrow_fee | `realized_trading_fee + realized_borrow_fee` | 0.074665999 |
| realized_fee_in_usd | Float64 | USD | 總手續費（USD 計） | `data_decoded.realized_fee_in_usd / 10^9 (USD_DECIMAL)` | 0.063989944 |

### 盈虧欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯 | 範例值 |
|----------|---------|------|------|---------|--------|
| realized_amount | Float64 | collateral_token | 實現金額（含費用） | `data_decoded.realized_amount / 10^(collateral_decimal)`；sign 由 `realized_amount_sign` 控制（false = 取反） | -0.110053556 |
| realized_pnl | Float64 | USD | 實現盈虧 | `(realized_amount - realized_fee) * realized_fee_in_usd / realized_fee`；若 `realized_fee == 0` 則為 0 | -0.157502573 |

> **realized_pnl 特殊邏輯**：當 `realized_fee == 0` 時（通常發生在期權 ITM 行權），`realized_pnl` 直接為 0。此時實際盈虧會在 RealizeOption 事件中計算（已廢棄）。

### 身分欄位

| 欄位名稱 | 資料類型 | 說明 | 計算邏輯 | 範例值 |
|----------|---------|------|---------|--------|
| distinct_id | String | 交易者地址（用於去重和篩選） | `data_decoded.user` | 0xc533c11ff... |
| sender | String | 實際發送交易的地址 | `event.sender` | 0x2afe65188... |
| is_cranker | Boolean | 是否由系統自動執行者觸發 | `event.sender != event.data_decoded.user` | true |

### 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260633136 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組名稱 | position |
| distinct_event_id | String | 事件唯一 ID | 8976a1037177ece5 |
| event_name | String | 事件名稱（固定值） | OrderFilled |
| log_index | Int64 | 交易中的 log 索引 | 3 |
| transaction_hash | String | 交易雜湊 | FfXNALJDnV... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 事件等級（固定 INFO） | INFO |

---

## 常見查詢模式

### 計算交易量（USD）

```sql
SELECT
  toDate(timestamp) AS day,
  sum(filled_price * filled_size) AS volume_usd
FROM OrderFilled
GROUP BY day
```

### 篩選開倉 vs 平倉

```sql
-- 僅開倉
WHERE order_type = 'Open'
-- 僅平倉（含減倉）
WHERE order_type = 'Close'
-- 僅加倉
WHERE order_type = 'Increase'
```

### 計算手續費分配

```sql
toDecimal64(realized_fee_in_usd * 0.7, 8) AS TLPFee,
toDecimal64(realized_fee_in_usd * 0.3, 8) AS ProtocolFee
```

### 查詢特定地址的交易

```sql
SELECT timestamp, base_token, order_type, side, filled_price, filled_size,
       filled_price * filled_size AS vol_usd, realized_pnl
FROM OrderFilled
WHERE distinct_id = '0x目標地址'
ORDER BY timestamp DESC
```

### 計算 OI 變化（用於 Open Interest 追蹤）

```sql
-- Open 事件增加 OI，Close 事件減少 OI
CASE
  WHEN order_type = 'Open' OR order_type = 'Increase'
    THEN filled_size * filled_price
  WHEN order_type = 'Close'
    THEN -1 * filled_size * filled_price
END AS oi_change
```

---

## 注意事項

- `filled_size` 的單位是 base_token 的原生單位（如 SUI 的個數），計算 USD 交易量需乘以 `filled_price`
- `realized_pnl` 僅在 Close 事件有實際意義；Open 事件的 `realized_pnl` 通常等於 `-realized_fee_in_usd`（僅反映手續費）
- `realized_amount` 的 sign 由 processor.ts 中的 `realized_amount_sign` 控制：`true` = 正值（交易者收到），`false` = 負值（交易者付出）
- `position_id` + `base_token` 組合唯一識別一個倉位
- `order_id` 全域唯一，可用於與 PlaceOrder 跨表關聯
- `is_cranker` 為 `true` 時，代表限價單觸價、TP/SL 或其他自動執行，`sender` 是 cranker 地址而非交易者

---

*建立於 2026-04-02，基於 processor.ts `position.onEventOrderFilledEvent` 和 orderfilled.csv 樣本資料。*
