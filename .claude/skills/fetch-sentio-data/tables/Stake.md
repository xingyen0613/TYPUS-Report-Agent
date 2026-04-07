# Stake

> 質押 LP 代幣事件。使用者將 LP 代幣（mTLP / iTLP）質押到 Stake Pool 以獲取額外 incentive 獎勵。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者質押 LP 代幣時 |
| 關聯事件 | MintLp → **Stake** → HarvestIncentive → Unstake → RedeemLp → BurnLp |
| Processor Handler | `stake_pool.onEventStakeEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 質押時間 | 原始事件時間 | 2026-04-02T09:14:12.589Z |
| index | Int64 | — | LP Pool 索引（0 = mTLP, 1 = iTLP） | 原始值 | 0 |
| stake_amount | Float64 | mTLP / iTLP | 質押的 LP 代幣數量 | `data_decoded.stake_amount / 10^9 (TLP_DECIMAL)` | 3385.605499419 |
| lp_token_type | String | — | LP 代幣的完整 Move 型別名稱 | 原始值（未經 parse_token） | 07be4837...::mtlp::MTLP |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 質押者地址 | 0x0599e3b3... |
| address | String | 合約地址 | 0xd280f3a0... |
| block_number | Int64 | 區塊編號 | 260689827 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | stake_pool |
| distinct_event_id | String | 事件唯一 ID | 99e5a112ca4ccd4a |
| event_name | String | 固定值 | Stake |
| log_index | Int64 | log 索引 | 3 |
| transaction_hash | String | 交易雜湊 | 2yhtuKcjMW... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日質押量

```sql
SELECT
    toDate(timestamp) AS day,
    sum(stake_amount) AS daily_stake
FROM Stake
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 淨質押量（搭配 Unstake）

```sql
WITH s AS (
    SELECT toDate(timestamp) AS day, sum(stake_amount) AS staked FROM Stake GROUP BY day
),
u AS (
    SELECT toDate(timestamp) AS day, sum(unstake_amount) AS unstaked FROM Unstake GROUP BY day
)
SELECT
    COALESCE(s.day, u.day) AS day,
    COALESCE(s.staked, 0) - COALESCE(u.unstaked, 0) AS net_stake
FROM s FULL OUTER JOIN u ON s.day = u.day
ORDER BY day ASC
```

---

## 注意事項

- `lp_token_type` 是原始 Move 型別字串（未經 `parse_token` 處理），例如 `07be...::mtlp::MTLP`
- `index = 0` 為 mTLP Pool，`index = 1` 為 iTLP Pool
- 質押操作通常伴隨 HarvestIncentive（先領取累積獎勵再重新質押），可透過 `transaction_hash` 確認
- 不涉及手續費

---

*建立於 2026-04-02，基於 processor.ts `stake_pool.onEventStakeEvent` 和 API 樣本資料。*
