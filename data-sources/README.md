# Typus 報告資料來源

## 目錄說明

### 1. typus-data/
存放核心營運數據（TVL、Users）

**檔案格式**：`Typus Data - TVL.csv`、`Typus Data - Users.csv`

**必需包含**：
- 當月 (M) 的 TVL 和 Users 數據
- 上個月 (M-1) 的 TVL 和 Users 數據（用於計算成長率）

**更新方式**：透過 `/fetch-typus-data` skill 自動從 Google Sheets 抓取

---

### 2. weekly-references/
存放當月的市場分析週報

**檔案命名**：`Week_DD Mon ~ DD Mon, YYYY.md`（含涵蓋日期範圍）

**用途**：AI 透過這些週報理解當月的宏觀市場背景

**更新方式**：透過 `/fetch-weekly-references` skill 自動從 Zerocap 抓取

---

### 3. monthly-history/
存放歷史月報

**檔案命名**：`january-2025.md`、`february-2025.md`

**用途**：幫助 AI 保持寫作風格和數據連續性

---

### 4. market-prices/
存放自動獲取的加密貨幣價格數據（月報用）

**檔案命名**：`january-2025.md`、`february-2025.md`

**更新方式**：透過 `/fetch-market-prices` skill 自動生成（monthly 模式）

---

### 5. sentio-data/
存放 Sentio 平台鏈上數據（週報用）

**檔案命名**：`week-N-month-year.md`（原始數據）、`week-N-month-year-brief.md`（Data Brief）

**包含數據**：TLP 價格、交易量、手續費、Trader P&L、清算量、DAU、OI、TVL 組成

**更新方式**：透過 `/fetch-sentio-data` skill 自動從 Sentio API 抓取

---

### 6. weekly-prices/
存放週度加密貨幣價格數據（週報用）

**檔案命名**：`week-N-month-year.md`

**更新方式**：透過 `/fetch-market-prices` skill 自動生成（weekly 模式）

---

### 7. weekly-history/
存放歷史週報最終版

**用途**：
- 歷史趨勢標記（ATH、連續上升/下降、異常值）
- 30 天績效比較與 Sharpe Ratio 計算（需 ≥4 週）
- 風格一致性參考

**注意**：每次週報完成後，請將最終版手動存入此目錄，以逐漸啟用歷史分析功能

---

### 8. editorial-guidelines.md
Typus 報告的編輯規範（語調、數字格式、寫作守則）

---

## 月報資料準備清單

- [ ] Typus Data 已更新至最新月份（或執行 `/fetch-typus-data`）
- [ ] Weekly References 包含當月所有週報（或執行 `/fetch-weekly-references`）
- [ ] Monthly History 包含上個月的最終版月報
- [ ] Market Prices 已透過 `/fetch-market-prices`（monthly 模式）取得

## 週報資料準備清單

- [ ] Sentio Data 已透過 `/fetch-sentio-data` 抓取當週數據
- [ ] Weekly Prices 已透過 `/fetch-market-prices`（weekly 模式）取得
- [ ] Weekly References 包含當週參考週報
