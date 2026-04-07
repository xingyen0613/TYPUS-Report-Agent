---
name: fetch-weekly-references
description: 自動從設定的外部來源（如 Zerocap）抓取並精簡每週加密市場報告，儲存至 data-sources/weekly-references/
user-invocable: true
allowed-tools: Read, Write, Glob, WebFetch, WebSearch
---

# 每週市場參考報告自動獲取

你是 Typus Finance 報告助手的市場參考資料獲取模組。你的任務是自動從外部來源抓取每週加密市場報告，精簡內容後儲存為結構化 markdown 檔案。

## 來源清單

```
1. 名稱：Zerocap
   列表頁 URL：https://zerocap.com/insights/weekly-crypto-market-wrap/
   日期偏移：-7 天（文章標題日期減 7 天 = 實際涵蓋週的週一）
   備註：文章 URL 格式不固定，必須從列表頁抓取實際連結
   發布規律：通常在週一/週二發布，涵蓋前一週
   跳週處理：Zerocap 偶爾會跳過某一週，這是正常的，直接跳過
```

日後新增其他來源時，在此區塊新增，各自定義偏移規則。

---

## 執行模式

**此 skill 必須透過 Agent tool 以 `model: sonnet` 委派給 sub-agent 執行，不得由主對話模型直接執行。**

執行步驟：
1. 使用 Agent tool，指定 `model: "sonnet"`
2. 將以下「執行流程」的完整內容作為 prompt 傳給 sub-agent（包含來源清單、所有步驟、輸出格式、錯誤處理）
3. Sub-agent 完成後，將結果回報給使用者

> 原因：此 skill 的核心任務（WebFetch + 精簡）屬於資料處理性質，不需要主對話等級的推理能力，使用 Sonnet 可大幅節省額度。

---

## 執行流程

### Step 0 — 偵測已有的覆蓋範圍

1. Glob `data-sources/weekly-references/Week_*.md` 找到所有既有檔案
2. 從檔名解析各週的週一日期（如 `Week_05 Jan ~ 11 Jan, 2026.md` → 取 `~` 前的部分 `Week_05 Jan` 提取 `05 Jan`，加上最後 `, YYYY` → `05 Jan 2026`）
3. 找出最晚的週一日期 = 已覆蓋邊界
4. 以今天的日期為上限（只抓已完整過去的週，即週日已過的週）

### Step 1 — 從各來源抓取文章列表

對每個設定的來源：

1. WebFetch 其列表頁 URL
2. 擷取每篇文章的：標題、日期、完整 URL
3. 套用該來源的日期偏移規則，計算實際涵蓋的週一日期

**Zerocap 日期偏移規則：**
- 文章標題中的日期（如 "2 February 2026"）代表發布日
- `實際涵蓋週的週一 = 文章標題日期 - 7 天`
- 例：文章 "2 February 2026" → 實際涵蓋 1月26日（週一）至 2月1日（週日）
- 例：文章 "9 February 2026" → 實際涵蓋 2月2日（週一）至 2月8日（週日）

### Step 2 — 找出缺少的週 & 向使用者確認

1. 比對可用文章（含計算後的週一日期）與既有檔案
2. 過濾掉：已有覆蓋的週、尚未完整結束的週（週日尚未過去）
3. 按週分組（日後多來源時：同一週可能有多個來源的文章）
4. 若某一週所有來源都沒有文章，則跳過（來源缺口，這是正常的）
5. 直接繼續執行（sub-agent 無法與使用者互動，不需確認）

### Step 3 — 逐篇抓取 & 精簡（compact）

對每個缺少的週，對每個有文章的來源：

1. WebFetch 完整文章 URL
2. 精簡內容，遵循以下規則：
   - **保留段落結構**：Market Theme、Key News、Technicals & Macro、Crypto、Spot Desk、Derivatives Desk、What to Watch（+ 來源若有額外段落也保留）
   - **壓縮**冗長敘述為密集、資訊豐富的段落
   - **保留所有**關鍵數字、百分比、價位、基點、具體數據
   - **保留**分析觀點、市場定位評論、交易建議
   - **移除**行銷廢話、重複說明、冗長過渡語
   - **品質對標**：以既有的 `Week_05 Jan ~ 11 Jan, 2026.md` 為參考標準（精簡密度、資訊保留程度）

### Step 4 — 儲存檔案

**檔名規則：**
- 格式：`Week_DD Mon ~ DD Mon, YYYY.md`，涵蓋週一至週日的完整日期範圍
- DD 為兩位數（補零），Mon 為三字母月份縮寫，YYYY 為四位數年份（跟在週日日期後）
- 週一與週日均保留月份縮寫（不省略），以便跨月的週也能清楚辨識
- 範例：
  - 涵蓋 Jan 26 – Feb 1, 2026 → `Week_26 Jan ~ 01 Feb, 2026.md`
  - 涵蓋 Feb 2 – Feb 8, 2026 → `Week_02 Feb ~ 08 Feb, 2026.md`
  - 涵蓋 Feb 16 – Feb 22, 2026 → `Week_16 Feb ~ 22 Feb, 2026.md`

**儲存路徑：** `data-sources/weekly-references/`

**多來源（未來）：** 同一週的所有來源合併到同一個檔案，以來源標頭分隔

### Step 5 — 回報完成

```
Weekly references 已更新：

新檔案：
  - Week_26 Jan ~ 01 Feb, 2026.md（Zerocap, 涵蓋：26 Jan – 1 Feb 2026）
  - Week_02 Feb ~ 08 Feb, 2026.md（Zerocap, 涵蓋：2 Feb – 8 Feb 2026）

已跳過（無來源覆蓋）：
  - Week of 19 Jan, 2026

下一步：/weekly-report-prepare 或 /weekly-report-generate
```

---

## 輸出格式

每個檔案必須遵循以下格式（與既有檔案一致）：

```markdown
### Week:DD Mon, YYYY

Period Covered: [週一日期全寫] – [週日日期全寫]
Source: ZeroCap Weekly Crypto Market Wrap – [原始文章日期全寫]
​

Market Theme:
[精簡段落，保留所有關鍵數據...]
​

Key News:
[精簡段落...]
​

Technicals & Macro:
[精簡段落...]
​

Crypto:
[精簡段落...]
​

Spot Desk:
[精簡段落...]
​

Derivatives Desk:
[精簡段落...]
​

What to Watch:
[精簡段落...]
​

```

**格式說明：**
- `​` = 零寬空格（U+200B），用作段落分隔符，與既有檔案格式一致
- 每個段落標題後加兩個空格再換行（trailing spaces for line break）
- Period Covered 和 Source 行後也加兩個空格
- 若來源文章包含額外段落（如 "End of the four year cycle?"、"ETH:"、"SOL:"），也保留並精簡
- 日期全寫格式：`5 January 2026`（不補零）

---

## 錯誤處理

- **列表頁抓取失敗**：回報錯誤並中止（無法判斷有哪些文章可用）
- **單篇文章 WebFetch 失敗**：回報錯誤，跳過該篇，繼續處理其他文章
- **沒有新文章需要抓取**：回報「所有 weekly references 已是最新」並結束
- **日期解析失敗**：回報該文章的日期無法解析，跳過並繼續

---

## 注意事項

- 只抓取已完整過去的週（週日已過）
- 嚴格遵循各來源的日期偏移規則
- 精簡品質必須與既有檔案一致：密集、資訊豐富、保留所有數據
- 不要編造或推測任何數據，所有數字必須來自原始文章
