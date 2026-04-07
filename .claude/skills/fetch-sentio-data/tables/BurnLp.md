# BurnLp

> LP 提取流動性事件。使用者完成贖回流程後，燒毀 LP 代幣（mTLP / iTLP），取回對應的代幣。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者在 RedeemLp 冷卻期結束後，燒毀 LP 代幣取回存入的代幣 |
| 關聯事件 | MintLp → RedeemLp → **BurnLp** |
| Processor Handler | `lp_pool.onEventBurnLpEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 提取時間 | 原始事件時間 | 2026-04-02T06:19:54.475Z |
| liquidity_token | String | — | 提取的代幣種類 | `parse_token(liquidity_token_type.name)` | USDC |
| index | Int64 | — | LP Pool 索引（0 = mTLP, 1 = iTLP） | 原始值 | 0 |
| burn_lp_amount | Float64 | mTLP / iTLP | 燒毀的 LP 代幣數量 | `data_decoded.burn_lp_amount / 10^9 (TLP_DECIMAL)` | 10.637692217 |
| burn_amount_usd | Float64 | USD | 燒毀的 LP 代幣價值（USD 計） | `data_decoded.burn_amount_usd / 10^9 (USD_DECIMAL)` | 8.654154184 |
| burn_fee_usd | Float64 | USD | 燒毀手續費（USD 計） | `data_decoded.burn_fee_usd / 10^9 (USD_DECIMAL)` | 0.008654155 |
| withdraw_token_amount | Float64 | liquidity_token | 實際取回的代幣數量（扣除手續費後） | `data_decoded.withdraw_token_amount / 10^(liquidity_token_decimal)` | 8.646787 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | LP 提取者地址 | 0x845c22be... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260649668 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | lp_pool |
| distinct_event_id | String | 事件唯一 ID | c2efa65f752ca024 |
| event_name | String | 固定值 | BurnLp |
| log_index | Int64 | log 索引 | 17 |
| transaction_hash | String | 交易雜湊 | A8doiznzkk... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 手續費計算（100% 歸 Protocol）

```sql
toDecimal64(burn_fee_usd, 8) AS ProtocolFee
-- BurnLp 手續費 100% 歸 Protocol，TLP Fee = 0
```

### 每日 LP 提取量

```sql
SELECT
    toDate(timestamp) AS day,
    sum(burn_amount_usd) AS daily_withdraw_usd
FROM BurnLp
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 淨流入流出（搭配 MintLp）

```sql
WITH mint AS (
    SELECT toDate(timestamp) AS day, sum(deposit_amount_usd) AS inflow
    FROM MintLp GROUP BY day
),
burn AS (
    SELECT toDate(timestamp) AS day, sum(burn_amount_usd) AS outflow
    FROM BurnLp GROUP BY day
)
SELECT
    COALESCE(m.day, b.day) AS day,
    COALESCE(m.inflow, 0) - COALESCE(b.outflow, 0) AS net_flow_usd
FROM mint m FULL OUTER JOIN burn b ON m.day = b.day
ORDER BY day ASC
```

---

## 注意事項

- **手續費分配**：BurnLp 手續費 100% 歸 Protocol Fee，TLP Fee = 0
- `withdraw_token_amount` 是使用者實際拿到的數量（`burn_amount_usd - burn_fee_usd` 對應的代幣量）
- `burn_lp_amount` 應與先前 RedeemLp 申請的 share 數量一致
- `liquidity_token` 是實際提取的代幣種類，不一定與當初 MintLp 存入的幣種相同（可能經過 Swap）

---

*建立於 2026-04-02，基於 processor.ts `lp_pool.onEventBurnLpEvent` 和 API 樣本資料。*
