# X (Twitter) 自動化方案

> 記錄 X 自動化發文的調研與規劃，供未來實作參考。

---

## 現況

目前週報/月報的 X Threads 內容由 `weekly-report-generate` / `monthly-report-generate` 自動生成，
格式已符合 X 發文規範（含 Hook、每則字數限制等）。
**發文步驟仍為手動**：複製 Threads 內容 → 在 X 介面逐則貼上。

---

## 目標

自動將已生成的 X Threads 草稿發布為 X 連推，減少手動操作。

---

## 可行方案調研

### 方案 A：官方 X API v2（需付費）

- **優點**：官方支援，穩定，支援 Thread 連推（reply chain）
- **限制**：
  - Free tier：只能寫入，每月 500 則
  - Basic tier：$100/月
  - 連推需逐則發文並記錄 tweet_id，作為下一則的 `reply.in_reply_to_tweet_id`
- **評估**：500 則/月對週報（約 8-10 則/週）夠用，但費用門檻高

### 方案 B：Typefully / Buffer 等第三方工具

- **Typefully**：原生支援 Thread 排程，免費方案有限額
- **Buffer**：支援多平台，Thread 功能需付費
- **流程**：手動貼到工具 → 排程發布，仍有操作步驟

### 方案 C：Playwright 瀏覽器自動化

- **原理**：用 Playwright 模擬登入 X，逐則輸入並送出
- **優點**：無 API 費用
- **風險**：違反 X ToS，帳號可能被封；X 前端改版後可能失效
- **評估**：不建議用於正式帳號

### 方案 D：Make / Zapier 自動化串接

- **原理**：觸發器（如 Google Sheets 新行 / GitHub push）→ 呼叫 X API 發文
- **優點**：低代碼，易維護
- **限制**：同樣依賴 X API，需付費 tier

---

## 建議實作路徑（待執行）

1. **短期**：維持現有手動流程，搭配 `/convert-report-format` + `/publish-medium` 優化 Medium 發布
2. **中期**：評估申請 X API Basic tier（若月報頻率提高）
3. **長期**：若申請 API，建立 `/post-x-threads` skill：
   - 讀取最新週報的 X Threads 區塊
   - 逐則呼叫 X API v2 POST /2/tweets，並串接 reply chain
   - 輸出每則 tweet URL 供確認

---

## X Threads 格式規範

詳見 `data-sources/x-threads-format.md`（若存在）或各 report-generate skill 中的 X Threads 章節。

- Hook 首則：吸引點擊，含週期標題
- 內文則：每則 ≤ 280 字元（英文）/ ≤ 140 字（含 CJK 計算）
- 結尾則：CTA（如 Full report on Medium + 連結）

---

*建立日期：2026-03-11*
