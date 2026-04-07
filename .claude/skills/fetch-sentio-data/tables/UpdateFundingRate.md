# UpdateFundingRate

> 資金費率更新事件。系統定期更新每個交易對的累計資金費率指數（全局事件，非針對個人倉位）。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 系統（cranker）定期更新資金費率指數時（每小時） |
| 關聯事件 | **UpdateFundingRate**（全局費率）→ RealizeFunding（個別倉位結算） |
| Processor Handler | `trading.onEventUpdateFundingRateEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 更新時間 | 原始事件時間 | 2026-04-02T11:00:31.788Z |
| base_token | String | — | 交易標的代幣 | `parse_token(base_token.name)` | CRCLX |
| cumulative_funding_rate_index | Int64 | — | 更新後的累計資金費率指數 | 原始值；`sign = false` 時取負 | -1947 |
| previous_cumulative_funding_rate_index | Int64 | — | 更新前的累計資金費率指數 | 原始值；`sign = false` 時取負 | -1947 |
| intervals_count | Int64 | — | 本次更新涵蓋的時間區間數 | 原始值 | 1 |
| new_funding_ts_ms | Int64 | 毫秒 | 新的資金費率時間戳 | 原始值 | 1775127600000 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 固定為空字串（系統事件，無使用者） | |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260714191 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | trading |
| distinct_event_id | String | 事件唯一 ID | ef853f49c241bcd4 |
| event_name | String | 固定值 | UpdateFundingRate |
| log_index | Int64 | log 索引 | 2 |
| transaction_hash | String | 交易雜湊 | 9KyaophPqu... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 查看特定交易對的費率變化

```sql
SELECT
    timestamp,
    previous_cumulative_funding_rate_index AS prev_index,
    cumulative_funding_rate_index AS curr_index,
    cumulative_funding_rate_index - previous_cumulative_funding_rate_index AS delta
FROM UpdateFundingRate
WHERE base_token = 'SUI'
ORDER BY timestamp DESC
LIMIT 50
```

### 費率變動最大的交易對

```sql
SELECT
    base_token,
    avg(cumulative_funding_rate_index - previous_cumulative_funding_rate_index) AS avg_delta,
    max(abs(cumulative_funding_rate_index - previous_cumulative_funding_rate_index)) AS max_abs_delta
FROM UpdateFundingRate
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY base_token
ORDER BY max_abs_delta DESC
```

---

## 注意事項

- **系統事件**：`distinct_id` 固定為空字串，由 cranker 自動觸發，非使用者操作
- **Sign Convention**：processor.ts 根據 `cumulative_funding_rate_index_sign` 決定正負。`sign = true` → 正值（多頭付空頭），`sign = false` → 負值（空頭付多頭）
- **與 RealizeFunding 的關係**：UpdateFundingRate 更新全局指數，RealizeFunding 則是個別倉位根據指數差異結算資金費。倉位的資金費 = `(當前 index - 倉位上次結算的 index) × position_size`
- `intervals_count` 通常為 1，表示一個時間區間；若系統延遲可能 > 1（補算多個區間）
- `cumulative_funding_rate_index = previous_cumulative_funding_rate_index` 時表示該區間無費率變化

---

*建立於 2026-04-02，基於 processor.ts `trading.onEventUpdateFundingRateEvent` 和 API 樣本資料。*
