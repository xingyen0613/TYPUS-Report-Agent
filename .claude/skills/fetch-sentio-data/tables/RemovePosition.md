# RemovePosition

> 倉位移除事件。倉位完全平倉或被清算後，系統移除該倉位並退還剩餘保證金。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 倉位完全關閉（平倉或清算）後，系統移除倉位記錄 |
| 關聯事件 | OrderFilled（Close）→ **RemovePosition** 或 Liquidate → **RemovePosition** |
| Processor Handler | `position.onEventRemovePositionEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 倉位移除時間 | 原始事件時間 | 2026-04-02T11:55:32.122Z |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | SUI |
| remaining_collateral_amount | Float64 | collateral_token | 退還給使用者的剩餘保證金 | `data_decoded.remaining_collateral_amount / 10^(collateral_token_decimal)` | 2.111650803 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 倉位擁有者地址 | 0xd32be7e9... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260726630 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | position |
| distinct_event_id | String | 事件唯一 ID | 9bc0abeffcd8fe74 |
| event_name | String | 固定值 | RemovePosition |
| log_index | Int64 | log 索引 | 6 |
| transaction_hash | String | 交易雜湊 | AYu9Y3fD5e... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日平倉/清算次數

```sql
SELECT
    toDate(timestamp) AS day,
    count(*) AS removed_positions
FROM RemovePosition
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 透過 transaction_hash 關聯平倉或清算事件

```sql
-- RemovePosition 沒有 base_token / position_id，
-- 需透過 transaction_hash 與同一交易中的 OrderFilled(Close) 或 Liquidate 關聯
SELECT r.timestamp, r.collateral_token, r.remaining_collateral_amount,
       o.base_token, o.position_id, o.realized_pnl
FROM RemovePosition r
JOIN OrderFilled o ON r.transaction_hash = o.transaction_hash
WHERE r.distinct_id = '0x目標地址'
ORDER BY r.timestamp DESC
```

---

## 注意事項

- **無 base_token / position_id 欄位**：RemovePosition 不記錄交易標的或倉位 ID，無法直接跨表關聯。需透過 `transaction_hash` 與同一交易中的 OrderFilled（Close）或 Liquidate 配對
- `remaining_collateral_amount` 是倉位關閉後退還給使用者的保證金（已扣除手續費和盈虧）
- 此事件是倉位生命週期的最後一步，每個倉位只會有一次 RemovePosition
- 不涉及額外手續費（手續費已在 OrderFilled 或 Liquidate 中扣除）

---

*建立於 2026-04-02，基於 processor.ts `position.onEventRemovePositionEvent` 和 API 樣本資料。*
