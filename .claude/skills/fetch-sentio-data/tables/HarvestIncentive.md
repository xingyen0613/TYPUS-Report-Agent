# HarvestIncentive

> 領取質押獎勵事件。使用者從 Stake Pool 領取累積的 incentive 獎勵。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者領取質押獎勵，或在 Stake/Unstake 時自動觸發（先結算獎勵） |
| 關聯事件 | Stake → **HarvestIncentive** → Unstake |
| Processor Handler | `stake_pool.onEventHarvestPerUserShareEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 領取時間 | 原始事件時間 | 2026-04-02T09:14:12.589Z |
| token | String | — | 獎勵代幣種類 | `parse_token(incentive_token_type.name)` | MTLP |
| harvest_amount | Float64 | token | 領取的獎勵數量 | `data_decoded.harvest_amount / 10^(token_decimal)` | 2.073627959 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 領取者地址 | 0x0599e3b3... |
| address | String | 合約地址 | 0xd280f3a0... |
| block_number | Int64 | 區塊編號 | 260689827 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | stake_pool |
| distinct_event_id | String | 事件唯一 ID | 0ab33ff65550c99c |
| event_name | String | 固定值 | HarvestIncentive |
| log_index | Int64 | log 索引 | 2 |
| transaction_hash | String | 交易雜湊 | 2yhtuKcjMW... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日獎勵發放量

```sql
SELECT
    toDate(timestamp) AS day,
    token,
    sum(harvest_amount) AS daily_harvest
FROM HarvestIncentive
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day, token
ORDER BY day ASC
```

### 特定地址的累計獎勵

```sql
SELECT
    token,
    sum(harvest_amount) AS total_harvest
FROM HarvestIncentive
WHERE distinct_id = '0x目標地址'
GROUP BY token
```

---

## 注意事項

- `harvest_amount = 0` 是正常的 — 當 Stake/Unstake 操作自動觸發 Harvest 時，若無累積獎勵則為 0
- `token` 經過 `parse_token` 處理（與 Stake/Unstake 的 `lp_token_type` 不同，後者是原始 Move 型別字串）
- HarvestIncentive 常與 Stake/Unstake 在同一交易中出現（先結算獎勵再操作質押），可透過 `transaction_hash` 關聯
- 不涉及手續費

---

*建立於 2026-04-02，基於 processor.ts `stake_pool.onEventHarvestPerUserShareEvent` 和 API 樣本資料。*
