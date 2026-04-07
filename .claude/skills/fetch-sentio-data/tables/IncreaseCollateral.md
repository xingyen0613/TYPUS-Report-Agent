# IncreaseCollateral

> 追加保證金事件。使用者為持倉追加保證金（降低槓桿、避免被清算）。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者主動為持倉追加保證金時 |
| 關聯事件 | OrderFilled（Open）→ **IncreaseCollateral** / ReleaseCollateral → OrderFilled（Close）|
| Processor Handler | `trading.onEventIncreaseCollateralEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 追加時間 | 原始事件時間 | 2026-04-02T04:40:54.46Z |
| base_token | String | — | 交易標的代幣 | `parse_token(base_token.name)` | MSTRX |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | SUI |
| position_id | Int64 | — | 倉位 ID | 原始值 | 0 |
| increased_collateral_amount | Float64 | collateral_token | 本次追加的保證金數量 | `data_decoded.increased_collateral_amount / 10^(collateral_token_decimal)` | 2 |
| remaining_collateral_amount | Float64 | collateral_token | 追加後的保證金總數量 | `data_decoded.remaining_collateral_amount / 10^(collateral_token_decimal)` | 5.961298536 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 倉位擁有者地址 | 0xc9922e4f... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260626976 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | trading |
| distinct_event_id | String | 事件唯一 ID | a18e0ab3177070e3 |
| event_name | String | 固定值 | IncreaseCollateral |
| log_index | Int64 | log 索引 | 4 |
| transaction_hash | String | 交易雜湊 | 2gGyFtj2Gw... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 查詢特定倉位的保證金追加歷史

```sql
SELECT timestamp, increased_collateral_amount, remaining_collateral_amount
FROM IncreaseCollateral
WHERE base_token = 'XAU' AND position_id = 30
ORDER BY timestamp ASC
```

### 每日追加保證金次數與金額

```sql
SELECT
    toDate(timestamp) AS day,
    count(*) AS increase_count,
    sum(increased_collateral_amount) AS total_increased
FROM IncreaseCollateral
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

---

## 注意事項

- **跨表關聯鍵**：`base_token` + `position_id` 可與 OrderFilled、ReleaseCollateral 等關聯同一倉位
- `remaining_collateral_amount` 是追加後的保證金總額，可用來追蹤倉位保證金水位變化
- 與 ReleaseCollateral 為對稱操作：Increase = 加保證金，Release = 提保證金
- 不涉及手續費
- 此為使用者主動操作，非系統自動觸發

---

*建立於 2026-04-02，基於 processor.ts `trading.onEventIncreaseCollateralEvent` 和 API 樣本資料。*
