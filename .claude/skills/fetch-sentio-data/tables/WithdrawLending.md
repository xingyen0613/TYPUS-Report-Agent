# WithdrawLending

> 平台借貸收益提取事件。平台方將 LP 池資金拿去放貸後，提取借貸收益時觸發。這是平台層級事件，與 LP 使用者無直接關聯。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 平台方提取 LP 池資金的借貸收益時 |
| 關聯事件 | 獨立於使用者操作，屬於平台層級事件 |
| Processor Handler | `lp_pool.onEventWithdrawLendingEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 提取時間 | 原始事件時間 | 2026-04-01T05:33:15.182Z |
| c_token | String | — | 借貸代幣（Collateral Token） | `parse_token(c_token_type.name)` | USDC |
| r_token | String | — | 獎勵代幣（Reward Token） | `parse_token(r_token_type.name)` | USDC |
| lending_interest | Float64 | c_token | 借貸利息收益 | `data_decoded.lending_interest / 10^(c_token_decimal)` | 13.237847 |
| protocol_share | Float64 | c_token | Protocol 分得的利息部分 | `data_decoded.protocol_share / 10^(c_token_decimal)` | 13.237847 |
| lending_reward | Float64 | r_token | 借貸獎勵（額外獎勵代幣） | `data_decoded.lending_reward / 10^(r_token_decimal)` | 0 |
| reward_protocol_share | Float64 | r_token | Protocol 分得的獎勵部分 | `data_decoded.reward_protocol_share / 10^(r_token_decimal)` | 0 |
| protocol_fee_usd | Float64 | USD | Protocol 總收益（USD 計） | `protocol_share * price_c_token + reward_protocol_share * price_r_token` | 13.234008334 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 固定為空字串（平台事件，無使用者） | |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260300911 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | lp_pool |
| distinct_event_id | String | 事件唯一 ID | 45b921c946bbf20a |
| event_name | String | 固定值 | WithdrawLending |
| log_index | Int64 | log 索引 | 2 |
| transaction_hash | String | 交易雜湊 | 8opYW3fsMs... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日借貸收益

```sql
SELECT
    toDate(timestamp) AS day,
    c_token,
    sum(protocol_fee_usd) AS daily_lending_revenue_usd
FROM WithdrawLending
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day, c_token
ORDER BY day ASC
```

### 累計借貸收益（Protocol Fee 組成部分）

```sql
SELECT
    c_token,
    sum(protocol_fee_usd) AS total_lending_fee_usd,
    sum(lending_interest) AS total_interest
FROM WithdrawLending
GROUP BY c_token
```

---

## 注意事項

- **平台層級事件**：`distinct_id` 固定為空字串，這不是使用者操作，而是平台方提取借貸收益
- **收益來源**：平台將 LP 池中的閒置資金進行借貸（如 Scallop、Navi 等借貸協議），產生額外收益
- **protocol_fee_usd 是即時計算的**：processor 使用 `getPriceBySymbol` 取得當下幣價乘以 protocol_share，因此 protocol_fee_usd 反映的是提取當下的幣價
- **lending_reward / reward_protocol_share**：目前樣本中均為 0，表示當前無額外獎勵代幣收益
- **protocol_share ≈ lending_interest**：目前樣本中兩者幾乎相等，暗示借貸利息全數歸 Protocol
- **手續費歸屬**：protocol_share 和 reward_protocol_share 100% 計入 Protocol Fee

---

*建立於 2026-04-02，基於 processor.ts `lp_pool.onEventWithdrawLendingEvent` 和 API 樣本資料。*
