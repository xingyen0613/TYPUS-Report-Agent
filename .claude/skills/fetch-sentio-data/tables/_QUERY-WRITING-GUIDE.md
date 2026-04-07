# Sentio SQL 查詢撰寫指南

> 撰寫自訂 SQL 查詢時的參考手冊。涵蓋 Sentio 平台的 SQL 方言、API 使用、常數對照、以及常見模式。

---

## 平台基本資訊

- **SQL 方言**：ClickHouse SQL（Sentio 底層使用 ClickHouse）
- **兩種 Engine**：
  - `"DEFAULT"` — 大多數查詢使用，支援完整 ClickHouse 語法
  - `"LITE"` — 簡單查詢，資源消耗較低
  - `"SMALL"` — 最小資源，適合簡單 SELECT

---

## API 請求模板

### SQL Endpoint

```
POST https://api.sentio.xyz/v1/analytics/typus/typus_perp/sql/execute
```

```json
{
  "sqlQuery": {
    "sql": "YOUR_SQL_HERE",
    "size": 1000
  },
  "engine": "DEFAULT"
}
```

> `version`、`source`、`cachePolicy` 等欄位皆為選用，不帶也能正常查詢。

### Metrics Endpoint

```
POST https://api.sentio.xyz/v1/insights/typus/typus_perp/query
```

用於時間序列資料（如 TLP 價格走勢、TVL），不需要寫 SQL。

### 共用 Headers（必要）

```
Content-Type: application/json
api-key: <API_KEY>
User-Agent: Mozilla/5.0
```

> **重要**：`User-Agent: Mozilla/5.0` 是必要的，否則會被 Cloudflare 擋 403。

---

## 時間處理

### 方式一：SQL 字串替換（推薦用於自訂查詢）

```sql
WHERE timestamp >= toDateTime('2026-02-02 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-02-09 00:00:00', 'UTC')
```

使用半開區間（`>=` 和 `<`），確保不重複計算邊界值。

### 方式二：SQL variables 參數

```json
"sqlQuery": {
  "sql": "SELECT ... WHERE timestamp >= {startTime} AND timestamp < {endTime}",
  "variables": {
    "startTime": "toDateTime('2026-02-02 00:00:00', 'UTC')",
    "endTime": "toDateTime('2026-02-09 00:00:00', 'UTC')"
  }
}
```

注意：variables 需在 SQL 中被 `{variableName}` 引用才會生效。

### 常用時間函數

| 函數 | 用途 | 範例 |
|------|------|------|
| `toDateTime(str, 'UTC')` | 字串轉時間 | `toDateTime('2026-02-02 00:00:00', 'UTC')` |
| `toDate(timestamp)` | 取日期部分 | `toDate(timestamp)` → `2026-02-02` |
| `toStartOfDay(timestamp)` | 取當日 00:00 | 用於日匯總 GROUP BY |
| `toStartOfHour(timestamp)` | 取整點小時 | 用於小時匯總 |
| `toStartOfWeek(timestamp, 1)` | 取該週一 | 第二參數 `1` = 以週一為一週起始 |

---

## 型別轉換

| 需求 | 語法 | 說明 |
|------|------|------|
| 金額精確計算 | `toDecimal64(value, 8)` | 避免浮點數精度問題，8 位小數 |
| 大數字 WoW 計算 | `CAST(val AS Decimal128(8))` | 防止 overflow |
| 字串轉浮點數 | `CAST(field AS Float64)` | — |
| 四捨五入 | `round(value, 2)` | 保留 2 位小數 |

---

## 從 processor.ts 提取的關鍵常數

### Decimal 常數

| 常數 | 值 | 用途 |
|------|-----|------|
| `USD_DECIMAL` | 9 | USD 金額欄位的原始精度（鏈上為 `value / 10^9`） |
| `PRICE_DECIMAL` | 8 | 價格欄位的原始精度（鏈上為 `value / 10^8`） |
| `TLP_DECIMAL` | 9 | TLP 數量的原始精度 |

> **注意**：processor.ts 在 emit 到 Sentio 時已完成 decimal 轉換，所以 SQL 查詢中看到的數值**已經是人類可讀的格式**（如 `filled_price = 3.42`，而非鏈上的 `342000000`）。不需要在 SQL 中再做除法。

### 手續費分配規則

| 常數 | 值 |
|------|-----|
| `PROTOCOL_FEE_SHARE` | 0.3（30%） |
| `TLP_FEE_SHARE` | 0.7（70%） |

**各事件手續費分配**：

| 事件 | 手續費欄位 | TLP Fee | Protocol Fee |
|------|----------|---------|-------------|
| OrderFilled | `realized_fee_in_usd` | 70% | 30% |
| RealizeFunding | `realized_funding_fee_usd` | 100% | 0% |
| MintLp | `mint_fee_usd` | 0% | 100% |
| BurnLp | `burn_fee_usd` | 0% | 100% |
| Swap | `fee_amount_usd` | 70% | 30% |
| Liquidate | `liquidator_fee_usd` | 70% | 30%（與一般手續費相同七三分） |
| Liquidate | `value_for_lp_pool_usd` | 100%（全額歸 LP） | 0%（不分帳） |

### Token Decimal 對照表

processor.ts 中 `token_decimal()` 函數定義：

| Decimal | Tokens |
|---------|--------|
| 9 | SUI, VSUI, HASUI, BUCK, AFSUI, CETUS, TURBOS, SCA, HIPPO, TYPUS, SPSUI, NAVX, BLUE, sSCA, STSUI, WAL, JPY, XAU |
| 8 | BTC, ETH, SOL, APT, INJ, SEI, JUP, LBTC, XBTC, HYPE, DOGE, XRP |
| 6 | USDC, WUSDC, USDT, DEEP, NS |
| 0 | FUD, LIQ, BLUB（特殊處理） |
| 9（預設） | 其他未列出的 token |

### Token Address 對照表

| Address (normalized) | Token |
|---------------------|-------|
| `0x027792d9fed7f9844eb4839566001bb6f6cb4804f66aa2da6fe1ee242d896881` | BTC |
| `0xaf8cd5edc19c4512f4259f0bee101a40d41ebed738ade5874359610ef8eeced5` | ETH |
| `0xb7844e289a8410e50fb3ca48d69eb9cf29e27d223ef90353fe1bd8e27ff8f3f8` | SOL |
| `0xdba34672e30cb065b1f93e3ab55318768fd6fef66c15942c9f7cb846e2f900e7` | USDC |
| `0x5d4b302506645c37ff133b98c4b50a5ae14841659738d6d733d59d0d217a93bf` | WUSDC |
| `0xc060006111016b8a020ad5b33834984a437aaa7d3c74c18e09a95d48aceab08c` | USDT |
| `0x5d1f47ea69bb0de31c313d7acf89b890dbb8991ea8e03c6c355171f84bb1ba4a` | TURBOS |
| `0x3a5143bb1196e3bcdfab6203d1683ae29edd26294fc8bfeafe4aaa9d2704df37` | APT |
| `0x76cb819b01abed502bee8a702b4c2d547532c12f25001c9dea795a5e631c26f1` | FUD |
| `0xf325ce1300e8dac124071d3152c5c5ee6174914f8bc2161e88329cf579246efc` | AFSUI |
| `0x549e8b69270defbfafd4f94e17ec44cdbdd99820b33bda2278dea3b9a32d3f55` | VSUI |
| `0x8993129d72e733985f7f1a00396cbd055bad6f817fee36576ce483c8bbb8b87b` | HIPPO |
| `0x3e8e9423d80e1774a7ca128fccd8bf5f1f7753be658c5e645929037f7c819040` | LBTC |

---

## 常見查詢模式

### 計算交易量（USD）

```sql
-- OrderFilled 交易量
SELECT filled_price * filled_size AS volume_usd FROM OrderFilled

-- Liquidate 清算交易量
SELECT position_size * trading_price AS volume_usd FROM Liquidate

-- 合併總交易量
WITH merged_vol AS (
  SELECT timestamp, filled_price * filled_size AS vol FROM OrderFilled
  UNION ALL
  SELECT timestamp, position_size * trading_price AS vol FROM Liquidate
)
SELECT sum(vol) FROM merged_vol
```

### 按日匯總

```sql
SELECT
  toDate(timestamp) AS day,
  sum(filled_price * filled_size) AS daily_volume
FROM OrderFilled
WHERE timestamp >= toDateTime('2026-02-02 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-02-09 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 篩選交易者地址

```sql
-- 用 distinct_id 篩選（= sender 地址）
WHERE distinct_id = '0x目標地址'
```

### 排除已知刷量地址

```sql
WHERE distinct_id NOT IN (
  '0x5db51fb378d12be4b6b79b7b23e86e920f8b7cbbfe82b394de65b243b09f2953',
  '0x57728a38a68e921d990d40ae5cfddf3a7b09599577ef006c9678cc84b4cc9cce',
  '0xb2c42812f18d448248adf2b65970a3f8dbe0d471a8cdd0e915857e3b2e5f90f5'
)
```

### WoW 對比（Week-over-Week）

```sql
-- 先聚合每週數據，再 LEFT JOIN 上週
FROM weekly_data AS curr
LEFT JOIN weekly_data AS prev
  ON curr.week_start = prev.week_start + INTERVAL 7 DAY
```

### Forward Fill（填補無事件時段）

```sql
-- 建立完整時間格線，LEFT JOIN 實際數據，用 COALESCE 填 0
WITH time_grid AS (
  SELECT arrayJoin(arrayMap(x -> toStartOfHour(toDateTime('起始時間') + x * 3600), range(168))) AS hour
),
data AS (
  SELECT toStartOfHour(timestamp) AS hour, sum(value) AS val
  FROM EventTable
  GROUP BY hour
)
SELECT time_grid.hour, COALESCE(data.val, 0) AS val
FROM time_grid LEFT JOIN data ON time_grid.hour = data.hour
```

---

## 常見陷阱

1. **表名反引號**：含特殊字元的表名建議加反引號（如 `` `RealizeFunding` ``、`` `Liquidate` ``）
2. **NULL 處理**：無事件的時段不會有 row，需要 LEFT JOIN + COALESCE 或 Forward Fill
3. **size 參數**：控制回傳最大行數，預設可能不夠。大查詢設 `"size": 10000`
4. **Sign Convention**：
   - `realized_pnl`：正值 = 交易者獲利，負值 = 交易者虧損
   - `realized_funding_fee_usd`：正值 = 交易者付出（多頭付空頭），負值 = 交易者收到
   - Trader P&L 中 Liquidate 和 RealizeFunding 需乘以 `-1` 轉為交易者視角
5. **Metrics vs SQL**：Counter 型 metrics（如 `trading_volume_usd`）是累加值，不適合直接用 SQL 查詢。用 SQL 查詢原始 event table 更靈活

---

*建立於 2026-04-02，基於 processor.ts 和現有 13 個 query 提取。*
