# ReleaseCollateral

> 釋放保證金事件。使用者從持倉中提取多餘的保證金（降低槓桿或取回浮盈部分）。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者主動從持倉中釋放部分保證金時 |
| 關聯事件 | OrderFilled（Open）→ **ReleaseCollateral** / IncreaseCollateral → OrderFilled（Close）|
| Processor Handler | `trading.onEventReleaseCollateralEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 釋放時間 | 原始事件時間 | 2026-04-02T04:51:47.464Z |
| base_token | String | — | 交易標的代幣 | `parse_token(base_token.name)` | MSTRX |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | USDC |
| position_id | Int64 | — | 倉位 ID | 原始值 | 1 |
| released_collateral_amount | Float64 | collateral_token | 本次釋放的保證金數量 | `data_decoded.released_collateral_amount / 10^(collateral_token_decimal)` | 3.48061 |
| remaining_collateral_amount | Float64 | collateral_token | 釋放後剩餘的保證金數量 | `data_decoded.remaining_collateral_amount / 10^(collateral_token_decimal)` | 1.682452 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 倉位擁有者地址 | 0x845c22be... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260629461 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | trading |
| distinct_event_id | String | 事件唯一 ID | d2747704bd3b2bd1 |
| event_name | String | 固定值 | ReleaseCollateral |
| log_index | Int64 | log 索引 | 4 |
| transaction_hash | String | 交易雜湊 | 4TFAwSqHEW... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 查詢特定倉位的保證金調整歷史

```sql
SELECT
    timestamp,
    released_collateral_amount,
    remaining_collateral_amount
FROM ReleaseCollateral
WHERE base_token = 'XAU' AND position_id = 30
ORDER BY timestamp ASC
```

### 搭配 IncreaseCollateral 查看保證金變動全貌

```sql
SELECT timestamp, 'Release' AS action, base_token, position_id,
       released_collateral_amount AS amount, remaining_collateral_amount AS remaining
FROM ReleaseCollateral
WHERE distinct_id = '0x目標地址'

UNION ALL

SELECT timestamp, 'Increase' AS action, base_token, position_id,
       increased_collateral_amount AS amount, remaining_collateral_amount AS remaining
FROM IncreaseCollateral
WHERE distinct_id = '0x目標地址'

ORDER BY timestamp ASC
```

---

## 注意事項

- **跨表關聯鍵**：`base_token` + `position_id` 可與 OrderFilled、IncreaseCollateral 等關聯同一倉位
- `remaining_collateral_amount` 是釋放後的剩餘保證金，可用來追蹤倉位保證金水位變化
- 不涉及手續費
- 此為使用者主動操作，非系統自動觸發

---

*建立於 2026-04-02，基於 processor.ts `trading.onEventReleaseCollateralEvent` 和 API 樣本資料。*
