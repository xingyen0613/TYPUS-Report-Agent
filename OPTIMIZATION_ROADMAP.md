# Typus Report - 優化方向追蹤

> 此文件記錄未來可探索的優化方向與已觀察的問題。

---

## 🔮 未來可探索的方向

### 方向 E：Zerocap 以外的週報來源
**優先級：低（視需求）**

`fetch-weekly-references` 的架構已設計為可擴展多來源。
在 SKILL.md 的「來源清單」區塊新增來源，即可讓 skill 自動合併同週多個來源。

---

### 方向 G：圖片生成自動化
**已完成（2026-03-16）**：所有圖表均已自動生成並上傳

目前進度：
- ✅ `{basename}-30d-performance.png`：由 `weekly-report-prepare` Step 4.5 透過 Sentio API 生成（30 天累積回報走勢圖）
- ✅ `{basename}-tlp-price.png`：由 `generate_charts.py` 生成，顯示 ~4 週 TLP 價格歷史（透過 Sentio API fallback 補齊前 3 週，本地 MD 缺少歷史時自動抓取）
- ✅ `{basename}-fee-breakdown.png`：由 `generate_charts.py` 生成
- ✅ `{basename}-oi-distribution.png`：由 `generate_charts.py` 生成（OI 分布含多空比）
- ✅ 其他圖表（Volume、DAU、PnL、Liquidation、OI History）：由 `generate_charts.py` 生成
- ✅ `/publish-medium` 自動掃描 `outputs/weekly/final/` 下所有對應 PNG，上傳至 Medium CDN 並嵌入草稿

**已知限制**：
- TLP Price 圖表 stats 欄顯示的週回報（Mon 日收盤 → Sun 日收盤）與 Data Brief 的回報（Mon 00:00 開盤 → Sun 最後小時收盤）有輕微差異，屬粒度差異，非 Bug

---

### 方向 H：X Threads 格式優化
優化 X Threads 的排版格式與結構

---

### 方向 I：各平台文章發表流程自動化
**Medium（已完整實作 2026-03-16）**：Playwright 直接建立草稿 + 自動上傳所有圖片
- `.claude/skills/publish-medium/import-to-medium.js`：Playwright 腳本，自動登入 + 建立草稿 + 上傳所有 PNG
- Session cookies 儲存於 `~/.config/typus-medium-session.json`（repo 外，不受 git 追蹤）
- 流程：`/convert-report-format` → `/publish-medium`（自動掃描所有對應 PNG，上傳至 CDN 並嵌入草稿，回傳草稿 URL）
- 所有圖表佔位符（30D、TLP Price、Fee Breakdown、OI Distribution 等）均已自動替換為 CDN URL

**X（待實作）**：
- 短期維持手動；中期評估 X API Basic tier；長期建立 `/post-x-threads` skill

---

## 🐛 已觀察問題（待確認後處理）

### Bug 1 — Sentio 數據檔案含未解析 Template Placeholder
**發現時間**：Week 4 February 2026 週報生成（2026-03-03）
**受影響檔案**：`data-sources/sentio-data/week-2-february-2026.md`
**症狀**：檔案中存在未替換的 Python f-string 變數，例如 `${total_pnl:,.2f}`、`${total_liq:,.2f}`、`${avg_dau:.0f}`

**可能原因**：`fetch-sentio-data` 在生成該週檔案時，部分 query 結果為空或計算失敗，導致插值變數未被替換就直接寫入。

**影響**：該週數據被用於 30D 計算時，PnL / 清算量 / DAU 數值不可信。

**建議改善（確認複現後實作）**：
- 在 `weekly-report-prepare` Step 1 驗證中加入 placeholder 偵測（掃描 `${...}` 格式字串）
- 或在 `fetch-sentio-data` 寫檔前對所有插值變數加保護，確保有實際數值才寫入

**狀態**：觀察後續是否再次出現，若複現則優先處理

---

### Bug 2 — Q8 與 Q10 OI 數值口徑歧義
**發現時間**：Week 4 February 2026 週報生成（2026-03-03）
**症狀**：Data Brief 同時存在兩組 OI 數字，來源時間點不同但未加說明：
- Q8（Opening Positions 快照）：抓取當下的即時值，非週末最終狀態
- Q10（OI History 週末最後一筆）：週日最後一小時數據，為本週最終 OI

**影響**：口徑不一致容易造成撰稿時誤引，或讀者對數字產生困惑。

**建議改善（低優先度，待後續調整）**：
- 在 Data Brief 的 OI 段落加注說明兩組數字的時間差
- 在 `weekly-report-generate` OI 段落規範中明確：週末 OI 以 Q10 為準，Q8 僅用於多空比分析

**狀態**：低優先度，待本季其他優化完成後處理

---

*最後更新：2026-03-16*
