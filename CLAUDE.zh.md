# CLAUDE.zh.md

此文件為中文版專案指南，提供給 Claude Code (claude.ai/code) 在此 repo 中操作時參考。

## 專案概覽

自動化報告生成系統，用於製作 Typus Finance 的 DeFi 協議週報與月報。報告發布至 Medium，並透過 X（Twitter）Threads 推廣。

## 週報工作流程（主要流程）

步驟須依序執行；若資料缺失，後面的步驟會自動觸發前面的步驟：

```
1. /fetch-sentio-data          ← 可手動觸發，也可在用戶說「幫我生成上週週報」時自動啟動
2. /weekly-report-prepare      ← 驗證資料、計算指標、生成圖表 + Data Brief
                                    ├── 週度價格缺失 → 自動觸發 /fetch-market-prices
                                    └── 市場參考不足 → 自動觸發 /fetch-weekly-references
3. /weekly-report-generate     ← 撰寫 Medium 文章 + 副標題 + X Threads
4. /convert-report-format      ← Markdown → Medium 優化 HTML
5. /publish-medium             ← Playwright：建立 Medium 草稿，自動上傳所有 PNG 至 CDN
```

**生成報告草稿後，必須繼續執行所有後續步驟**（HTML 轉換 → Medium 發布 → X Threads URL 更新），除非明確要求暫停。

用戶貼回已發布的 Medium URL 時，自動更新對應 X Threads 檔案中的 LINK 佔位符。

## 月報工作流程

```
1. /monthly-report-prepare     ← 自動觸發 /fetch-typus-data 和 /fetch-weekly-references（如有缺失）
2. /monthly-report-generate    ← 自動觸發 /fetch-market-prices（如有缺失）
3. /convert-report-format
4. /publish-medium
```

## 資料來源與命名規則

| 資料類型 | 目錄 | 命名格式 |
|----------|------|---------|
| Sentio 鏈上數據（週報） | `data-sources/sentio-data/` | `week-{N}-{month}-{year}.md` |
| Weekly Data Brief | `data-sources/sentio-data/` | `week-{N}-{month}-{year}-brief.md` |
| 週度價格 | `data-sources/weekly-prices/` | `week-{N}-{month}-{year}.md` |
| 月度價格 | `data-sources/market-prices/` | `{month}-{year}.md` |
| 市場參考週報 | `data-sources/weekly-references/` | `Week_DD Mon ~ DD Mon, YYYY.md` |
| Typus TVL/Users | `data-sources/typus-data/` | 從 Google Sheets 下載的 CSV |

**輸出路徑**：`outputs/weekly/draft/` → `outputs/weekly/final/`（月報同理）

**Weekly References 日期規則**：Zerocap 文章標題日期減 7 天 = 實際涵蓋週的週一。例如文章標題 "2 February 2026" → 檔案命名 `Week_26 Jan ~ 01 Feb, 2026.md`

## Skills 架構

所有 skills 存放於 `.claude/skills/`（本地 skills，優先級高於全局 skills）。編輯任一 skill 目錄下的 `SKILL.md` 即可立即生效。

關鍵實作檔案：
- `.claude/skills/generate-charts/generate_charts.py` — 生成 TLP Price（~4 週歷史）、Fee Breakdown、OI Distribution、Volume、DAU、PnL、Liquidation 等 PNG 圖表
- `.claude/skills/publish-medium/import-to-medium.js` — Playwright 腳本；自動上傳 `outputs/weekly/final/` 下所有 PNG 至 Medium CDN，將 `[Image: ...]` 佔位符替換為 CDN URL
- `.claude/skills/fetch-sentio-data/.api-key` — Sentio API Key（已加入 .gitignore，一行純文字）

Medium Session Cookies 存放於 `~/.config/typus-medium-session.json`（repo 外，不受 git 追蹤）。

`/fetch-sentio-data` 也支援**自訂查詢模式（Ad-hoc Custom Query）**，不限於 13 個標準 Query。當用戶要求特定鏈上數據時（例如：某交易對的交易量、手續費最高的前幾筆、某 position 的完整歷史），應進入自訂查詢模式：讀取 `tables/` 標註文件 → 撰寫 SQL → 與用戶確認後執行。

## TVL 計算公式

系統忽略舊的 TVL_Total 欄位，使用以下公式：
- **Total TVL** = TVL_Perps + DOV TVL + (2 × SAFU TVL)
- **Options TVL** = DOV TVL + (2 × SAFU TVL)

## 數據呈現規則

- OI、DAU、Trader P&L 等絕對值偏小的數據：禁止直接呈現原始數字，改用 WoW% 或趨勢語言。
- 週報：600–800 字 Medium 文章，無表格，各段落使用敘事型標題。

## 報告架構

**週報（8 段）**：Title → TL;DR（單段敘事）→ Market Context → LP Performance → 30-Day Performance → Trader Performance → OI & Sentiment → 收尾 + CTA（`https://typus.finance/tlp/`）

**月報（10 點）**：Title → TL;DR → Market Pulse & TVL → Performance Deep Dive → User Engagement → Product Shipped → Roadmap Update → Community & Ecosystem → Building Momentum → CTA

**X Threads**：1 條引子 + 4 條編號推文（1/4…4/4），每條 200–280 字符，除引子外不使用 emoji，最後一條包含 Medium 連結佔位符。

## 文件維護

- 未來優化方向 → `OPTIMIZATION_ROADMAP.md`
- 新功能或改動測試成功後 → 更新 `OPTIMIZATION_ROADMAP.md` 與 `QUICKSTART.md`
