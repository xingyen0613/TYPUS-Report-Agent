# Unstake

> 解除質押 LP 代幣事件。使用者從 Stake Pool 取回 LP 代幣，通常是為了後續贖回（RedeemLp → BurnLp）。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者解除 LP 代幣質押時 |
| 關聯事件 | Stake → HarvestIncentive → **Unstake** → RedeemLp → BurnLp |
| Processor Handler | `stake_pool.onEventUnstakeEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 解除質押時間 | 原始事件時間 | 2026-04-02T06:19:54.475Z |
| index | Int64 | — | LP Pool 索引（0 = mTLP, 1 = iTLP） | 原始值 | 0 |
| unstake_amount | Float64 | mTLP / iTLP | 解除質押的 LP 代幣數量 | `data_decoded.unstake_amount / 10^9 (TLP_DECIMAL)` | 10.637692217 |
| lp_token_type | String | — | LP 代幣的完整 Move 型別名稱 | 原始值（未經 parse_token） | 07be4837...::mtlp::MTLP |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 解除質押者地址 | 0x845c22be... |
| address | String | 合約地址 | 0xd280f3a0... |
| block_number | Int64 | 區塊編號 | 260649668 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | stake_pool |
| distinct_event_id | String | 事件唯一 ID | 8bd533e805a7773a |
| event_name | String | 固定值 | Unstake |
| log_index | Int64 | log 索引 | 9 |
| transaction_hash | String | 交易雜湊 | A8doiznzkk... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日解除質押量

```sql
SELECT
    toDate(timestamp) AS day,
    sum(unstake_amount) AS daily_unstake
FROM Unstake
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

---

## 注意事項

- `lp_token_type` 是原始 Move 型別字串（未經 `parse_token` 處理）
- `index = 0` 為 mTLP Pool，`index = 1` 為 iTLP Pool
- Unstake 通常與 RedeemLp 在同一交易中發生（先解除質押，再申請贖回），可透過 `transaction_hash` 確認
- 不涉及手續費

---

*建立於 2026-04-02，基於 processor.ts `stake_pool.onEventUnstakeEvent` 和 API 樣本資料。*
