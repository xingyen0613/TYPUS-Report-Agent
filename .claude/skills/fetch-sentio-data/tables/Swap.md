# Swap

> LP 池內資產互換事件。使用者在 LP Pool 中將一種代幣換成另一種代幣。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者在 LP Pool 執行代幣互換時 |
| 關聯事件 | 獨立事件，不屬於交易或 LP 生命週期 |
| Processor Handler | `lp_pool.onEventSwapEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 互換時間 | 原始事件時間 | 2026-03-19T08:38:53.878Z |
| from_token | String | — | 賣出的代幣種類 | `parse_token(from_token_type.name)` | USDC |
| to_token | String | — | 買入的代幣種類 | `parse_token(to_token_type.name)` | SUI |
| from_amount | Float64 | from_token | 賣出數量 | `data_decoded.from_amount / 10^(from_token_decimal)` | 1 |
| to_amount | Float64 | to_token | 實際收到的數量 | `data_decoded.actual_to_amount / 10^(to_token_decimal)` | 1.040846998 |
| fee_amount | Float64 | from_token | 手續費（以賣出代幣計） | `data_decoded.fee_amount / 10^(from_token_decimal)` | 0.001534 |
| fee_amount_usd | Float64 | USD | 手續費（USD 計） | `data_decoded.fee_amount_usd / 10^9 (USD_DECIMAL)` | 0.001534427 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 互換者地址 | 0xdc72506f... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 255946317 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | lp_pool |
| distinct_event_id | String | 事件唯一 ID | b61089dc1439b277 |
| event_name | String | 固定值 | Swap |
| log_index | Int64 | log 索引 | 5 |
| transaction_hash | String | 交易雜湊 | BqfcfxUBQw... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日 Swap 量

```sql
SELECT
    toDate(timestamp) AS day,
    sum(fee_amount_usd) AS daily_swap_fee_usd,
    count(*) AS swap_count
FROM Swap
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 手續費計算（30% Protocol / 70% TLP）

```sql
SELECT
    toDecimal64(fee_amount_usd * 0.3, 8) AS ProtocolFee,
    toDecimal64(fee_amount_usd * 0.7, 8) AS TlpFee
FROM Swap
```

### 按交易對統計

```sql
SELECT
    from_token,
    to_token,
    count(*) AS swap_count,
    sum(fee_amount_usd) AS total_fee_usd
FROM Swap
GROUP BY from_token, to_token
ORDER BY swap_count DESC
```

---

## 注意事項

- **手續費分配**：Swap 手續費 30% 歸 Protocol Fee，70% 歸 TLP Fee（與 MintLp/BurnLp 的 100% Protocol 不同）
- `fee_amount` 單位是 `from_token`（賣出代幣），不是 USD
- `to_amount` 是使用者實際收到的數量（已扣除手續費後的淨額）
- 目前樣本資料顯示主要是 SUI ↔ USDC 的互換

---

*建立於 2026-04-02，基於 processor.ts `lp_pool.onEventSwapEvent` 和 API 樣本資料。*
