# Liquidate

> 強制清算事件。當交易者的倉位保證金不足時，由系統（cranker）觸發強制平倉。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 倉位保證金率低於清算線時，由 cranker 自動執行 |
| 關聯事件 | OrderFilled (Open) → ... → **Liquidate** → RemovePosition |
| Processor Handler | `trading.onEventLiquidateEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 清算發生時間 | 原始事件時間 | 2026-04-02T03:42:39.998Z |
| base_token | String | — | 被清算倉位的交易標的 | `parse_token(base_token.name)` | HYPE |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | SUI |
| position_id | Int64 | — | 被清算的倉位 ID | 原始值 | 269 |
| trading_price | Float64 | USD | 實際清算成交價格（市場波動大時可能因滑價與 estimated_liquidation_price 有誤差） | `data_decoded.trading_price / 10^8 (PRICE_DECIMAL)` | 35.12890909 |
| collateral_price | Float64 | USD | 清算時的保證金代幣價格 | `data_decoded.collateral_price / 10^8 (PRICE_DECIMAL)` | 0.85810891 |
| position_size | Float64 | base_token | 被清算的倉位大小（逐倉清算，整個倉位一次全部清算） | `data_decoded.u64_padding[0] / 10^(base_token_decimal)`；若 `u64_padding` 為空則為 undefined | 1.9 |
| estimated_liquidation_price | Float64 | USD | 理論清算價格（觸發清算的門檻價格，實際成交價為 trading_price，兩者可能因滑價有差異） | `data_decoded.u64_padding[1] / 10^8 (PRICE_DECIMAL)`；若無則為 undefined | 35.1408377 |

### 費用 / 金額欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯 | 範例值 |
|----------|---------|------|------|---------|--------|
| liquidator_fee | Float64 | collateral_token | 清算手續費（以保證金代幣計）。清算人（Liquidator）即 LP 存款人（Depositor），作為交易對手方。此費用與 Protocol 七三分帳後計入 LP Pool | `data_decoded.realized_liquidator_fee / 10^(collateral_decimal)` | 0.777814172 |
| liquidator_fee_usd | Float64 | USD | 清算手續費（USD 計） | `liquidator_fee * collateral_price` | 0.667449271 |
| value_for_lp_pool | Float64 | collateral_token | 扣除手續費後的倉位剩餘價值（以保證金代幣計）。直接作為 LP 收益全額計入 LP Pool，不與 Protocol 分帳 | `data_decoded.realized_value_for_lp_pool / 10^(collateral_decimal)` | 1.143934675 |
| value_for_lp_pool_usd | Float64 | USD | 扣除手續費後的倉位剩餘價值（USD 計） | `value_for_lp_pool * collateral_price` | 0.981620537 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 被清算者的地址 | 0x9b22882... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260613846 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | trading |
| distinct_event_id | String | 事件唯一 ID | 4bf74c9295ca145d |
| event_name | String | 固定值 | Liquidate |
| log_index | Int64 | log 索引 | 6 |
| transaction_hash | String | 交易雜湊 | FQVizoUL3h... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 計算清算交易量（USD）

```sql
SELECT position_size * trading_price AS volume_usd FROM Liquidate
```

### 每日清算量（排除刷量地址）

```sql
SELECT
    toDate(timestamp) AS day,
    sum(position_size * trading_price) AS daily_liquidation_usd
FROM Liquidate
WHERE distinct_id NOT IN (
    '0x5db51fb378d12be4b6b79b7b23e86e920f8b7cbbfe82b394de65b243b09f2953',
    '0x57728a38a68e921d990d40ae5cfddf3a7b09599577ef006c9678cc84b4cc9cce',
    '0xb2c42812f18d448248adf2b65970a3f8dbe0d471a8cdd0e915857e3b2e5f90f5'
)
GROUP BY day
ORDER BY day ASC
```

### 在 Trader P&L 計算中的用法

```sql
-- 清算損失 = LP 獲得 + 清算人費用，取反為交易者視角
CAST((value_for_lp_pool_usd + liquidator_fee_usd) AS Float64) * (-1) AS Pnl
```

### 在交易量合併中的用法

```sql
-- 與 OrderFilled 合併計算總交易量
WITH merged_vol AS (
  SELECT timestamp, filled_price * filled_size AS vol FROM OrderFilled
  UNION ALL
  SELECT timestamp, position_size * trading_price AS vol FROM Liquidate
)
```

---

## 注意事項

- **逐倉清算**：清算為單一倉位全部清算，不會部分清算
- **滑價**：`estimated_liquidation_price` 是理論觸發價格，`trading_price` 是實際成交價格，市場劇烈波動時兩者可能有差異
- **費用分帳**：
  - `liquidator_fee`：與 Protocol 七三分帳（70% LP / 30% Protocol）
  - `value_for_lp_pool`：全額歸 LP Pool，不與 Protocol 分帳
- 清算交易量用 `position_size * trading_price`（不同於 OrderFilled 的 `filled_price * filled_size`）
- Trader P&L 中，清算損失 = `(value_for_lp_pool_usd + liquidator_fee_usd) * (-1)`
- `position_size` 和 `estimated_liquidation_price` 來自 `u64_padding` 陣列，早期資料可能缺失（為 null/undefined）
- 查詢清算數據時建議排除已知刷量地址（見 `_QUERY-WRITING-GUIDE.md`）
- `distinct_id` 是被清算者，不是執行清算的 cranker

*建立於 2026-04-02，基於 processor.ts `trading.onEventLiquidateEvent` 和 API 樣本資料。*
