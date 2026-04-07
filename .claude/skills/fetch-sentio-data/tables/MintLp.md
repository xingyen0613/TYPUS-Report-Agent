# MintLp

> LP 注入流動性事件。使用者將代幣存入 LP Pool，獲得對應的 TLP token。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者存入代幣兌換 LP 代幣（mTLP / iTLP）時 |
| 關聯事件 | **MintLp** → Stake（質押 LP 代幣獲取 incentive）/ RedeemLp → BurnLp |
| Processor Handler | `lp_pool.onEventMintLpEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 存入時間 | 原始事件時間 | 2026-04-02T06:19:40.737Z |
| liquidity_token | String | — | 存入的代幣種類 | `parse_token(liquidity_token_type.name)` | SUI |
| index | Int64 | — | LP Pool 索引（0 = mTLP, 1 = iTLP） | 原始值 | 0 |
| deposit_amount | Float64 | liquidity_token | 存入數量（以存入代幣計） | `data_decoded.deposit_amount / 10^(liquidity_token_decimal)` | 10 |
| deposit_amount_usd | Float64 | USD | 存入價值（USD 計） | `data_decoded.deposit_amount_usd / 10^9 (USD_DECIMAL)` | 8.6540707 |
| mint_fee_usd | Float64 | USD | 鑄造手續費（USD 計） | `data_decoded.mint_fee_usd / 10^9 (USD_DECIMAL)` | 0 |
| minted_lp_amount | Float64 | mTLP / iTLP | 獲得的 LP 代幣數量（依 index 決定：0 = mTLP, 1 = iTLP） | `data_decoded.minted_lp_amount / 10^9 (TLP_DECIMAL)` | 10.637692217 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | LP 存款人地址 | 0x845c22be... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260649617 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | lp_pool |
| distinct_event_id | String | 事件唯一 ID | c6021e30a2107973 |
| event_name | String | 固定值 | MintLp |
| log_index | Int64 | log 索引 | 7 |
| transaction_hash | String | 交易雜湊 | 3zPLXVzJfK... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日 LP 存入量

```sql
SELECT
    toDate(timestamp) AS day,
    sum(deposit_amount_usd) AS daily_deposit_usd
FROM MintLp
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 手續費計算（100% 歸 Protocol）

```sql
toDecimal64(mint_fee_usd, 8) AS ProtocolFee
-- MintLp 手續費 100% 歸 Protocol，TLP Fee = 0
```

### 按幣種統計存入

```sql
SELECT liquidity_token, sum(deposit_amount_usd) AS total_usd
FROM MintLp
GROUP BY liquidity_token
```

---

## 注意事項

- **手續費分配**：MintLp 手續費 100% 歸 Protocol Fee，TLP Fee = 0
- `index = 0` 為 mTLP Pool，`index = 1` 為 iTLP Pool
- `mint_fee_usd` 目前為 0，此費率由 Protocol 調整，未來可能啟用
- `minted_lp_amount` 是使用者實際獲得的 LP 代幣數量（mTLP 或 iTLP），可用 `deposit_amount_usd / minted_lp_amount` 推算當時 LP 代幣價格
- 使用者拿到 LP 代幣後可進行 Stake（質押）獲取額外 incentive

---

*建立於 2026-04-02，基於 processor.ts `lp_pool.onEventMintLpEvent` 和 API 樣本資料。*
