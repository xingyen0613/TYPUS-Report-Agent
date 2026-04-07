# RedeemLp

> LP 發起贖回請求事件。使用者申請提取流動性，進入冷卻期等待，冷卻期結束後才能執行 BurnLp 取回代幣。

## 基本資訊

| 屬性 | 值 |
|------|-----|
| 事件觸發時機 | 使用者發起 LP 贖回請求時（開始冷卻期） |
| 關聯事件 | MintLp → **RedeemLp** → BurnLp |
| Processor Handler | `lp_pool.onEventRedeemEvent` |

---

## 欄位說明

### 核心欄位

| 欄位名稱 | 資料類型 | 單位 | 說明 | 計算邏輯（from processor.ts） | 範例值 |
|----------|---------|------|------|-------------------------------|--------|
| timestamp | DateTime | UTC | 贖回申請時間 | 原始事件時間 | 2026-04-02T06:19:54.475Z |
| share | Float64 | mTLP / iTLP | 申請贖回的 LP 代幣數量 | `data_decoded.share / 10^9 (TLP_DECIMAL)` | 10.637692217 |

### 身分 / 系統欄位

| 欄位名稱 | 資料類型 | 說明 | 範例值 |
|----------|---------|------|--------|
| distinct_id | String | LP 贖回申請者地址 | 0x845c22be... |
| address | String | 合約地址 | 0x900321918... |
| block_number | Int64 | 區塊編號 | 260649668 |
| chain | String | 區塊鏈 | sui_mainnet |
| contract | String | 合約模組 | lp_pool |
| distinct_event_id | String | 事件唯一 ID | ca1ede668f66ce66 |
| event_name | String | 固定值 | RedeemLp |
| log_index | Int64 | log 索引 | 10 |
| transaction_hash | String | 交易雜湊 | A8doiznzkk... |
| transaction_index | Int64 | 交易在區塊中的索引 | 0 |
| message | String | 附加訊息（通常為空） | |
| severity | String | 固定 INFO | INFO |

---

## 常見查詢模式

### 每日贖回申請量

```sql
SELECT
    toDate(timestamp) AS day,
    sum(share) AS daily_redeem_share
FROM RedeemLp
WHERE timestamp >= toDateTime('2026-03-24 00:00:00', 'UTC')
  AND timestamp < toDateTime('2026-03-31 00:00:00', 'UTC')
GROUP BY day
ORDER BY day ASC
```

### 贖回到提取的延遲（搭配 BurnLp）

```sql
-- RedeemLp 與 BurnLp 透過 distinct_id + share ≈ burn_lp_amount 配對
SELECT
    r.timestamp AS redeem_time,
    b.timestamp AS burn_time,
    dateDiff('minute', r.timestamp, b.timestamp) AS cooldown_minutes,
    r.share AS redeem_share,
    b.burn_lp_amount
FROM RedeemLp r
JOIN BurnLp b
    ON r.distinct_id = b.distinct_id
    AND abs(r.share - b.burn_lp_amount) < 0.001
    AND b.timestamp > r.timestamp
    AND b.timestamp < r.timestamp + INTERVAL 7 DAY
ORDER BY r.timestamp DESC
LIMIT 20
```

---

## 注意事項

- **無 index 欄位**：RedeemLp 不記錄 LP Pool 索引（mTLP / iTLP），需透過後續 BurnLp 的 `index` 欄位判斷
- **share = 後續 BurnLp 的 burn_lp_amount**：可透過數值匹配確認同一筆贖回流程
- **冷卻期**：RedeemLp 到 BurnLp 之間有冷卻期（由 Protocol 設定），使用者無法立即提取
- RedeemLp 本身不涉及手續費，手續費在 BurnLp 階段收取
- 此事件是 LP 提取流程的中間步驟，完整流程：MintLp（存入）→ RedeemLp（申請提取）→ BurnLp（實際提取）

---

*建立於 2026-04-02，基於 processor.ts `lp_pool.onEventRedeemEvent` 和 API 樣本資料。*
