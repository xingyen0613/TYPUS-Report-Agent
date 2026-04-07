# RealizeFunding

> 資金費率結算事件。持倉期間由系統（cranker）週期性觸發，根據多空比例向持倉者收取或發放資金費。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 兩種方式：(1) 使用者手動結算；(2) 對倉位有異動時自動觸發（如關倉、加倉等）。可視為獨立事件，不一定伴隨其他事件出現 |
| 關聯事件 | OrderFilled (Open) → **RealizeFunding** (持倉期間) → OrderFilled (Close) / Liquidate |
| Processor Handler | `position.onEventRealizeFundingEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 結算時間 | 原始事件時間 | 2026-04-02T07:11:42.007Z |
| base_token | String | — | 倉位的交易標的 | `parse_token(symbol.base_token.name)` | SUI |
| collateral_token | String | — | 保證金代幣 | `parse_token(collateral_token.name)` | SUI |
| position_id | Int64 | — | 被結算的倉位 ID | 原始值 | 2134 |
| realized_funding_fee | Float64 | collateral_token | 資金費（以保證金代幣計）。正值 = 交易者付出；負值 = 交易者收到 | `data_decoded.realized_funding_fee / 10^(collateral_decimal)`；sign 由 `realized_funding_sign` 控制（false = 取反） | 0.001421836 |
| realized_funding_fee_usd | Float64 | USD | 資金費（USD 計）。正值 = 交易者付出；負值 = 交易者收到 | `data_decoded.realized_funding_fee_usd / 10^9 (USD_DECIMAL)`；sign 同上 | 0.001226629 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | 持倉者地址 | 0xc533c11ff... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260661563 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | position |
| distinct_event_id | String | 事件唯一 ID | d715021cb6ae58d2 |
| event_name | String | 固定值 | RealizeFunding |
| log_index | Int64 | log 索引 | 5 |
| transaction_hash | String | 交易雜湊 | CuUpqUTSUW... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 在 Trader P&L 計算中的用法

```sql
-- 資金費取反為交易者視角的損益
-- 正值（交易者付出）→ 乘以 -1 → 負 P&L（交易者損失）
-- 負值（交易者收到）→ 乘以 -1 → 正 P&L（交易者獲利）
CAST(realized_funding_fee_usd AS Float64) * (-1) AS Pnl
```

### 每日資金費收入（LP 視角）

```sql
SELECT
    toDate(timestamp) AS day,
    sum(realized_funding_fee_usd) AS daily_funding_fee_usd
FROM RealizeFunding
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 查詢特定倉位的資金費歷史

```sql
SELECT timestamp, realized_funding_fee, realized_funding_fee_usd
FROM RealizeFunding
WHERE position_id = 2134 AND base_token = 'SUI'
ORDER BY timestamp ASC
```

---

## 注意事項

- **Sign Convention**：`realized_funding_fee` / `realized_funding_fee_usd` 正值 = 交易者付出，負值 = 交易者收到
- **多空方向**：OI 較多的一方付給較少的一方（如多頭 OI > 空頭 OI，則多頭付費、空頭收費）
- **累積機制**：每小時在後台累積增減，但不會每小時都觸發 RealizeFunding 事件。實際結算時機為使用者手動觸發或倉位異動時
- **Trader P&L 計算時需乘以 -1**：因為正值代表交易者的支出，轉換為 P&L 損失
- **手續費分配**：資金費 100% 歸 TLP Fee（LP 收益），Protocol 不分帳
- processor.ts 中 sign 由 `realized_funding_sign` 控制：`true` = 正值（付出），`false` = 取反為負值（收到）
- 同一個倉位在持倉期間會有多筆 RealizeFunding 事件

---

*建立於 2026-04-02，基於 processor.ts `position.onEventRealizeFundingEvent` 和 API 樣本資料。*
