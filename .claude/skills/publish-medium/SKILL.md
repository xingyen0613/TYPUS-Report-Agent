---
name: publish-medium
description: 使用 Playwright 自動在 Medium 建立草稿（直接貼入內容，無需 GitHub Pages）
user-invocable: true
allowed-tools: Glob, Bash
---

# Medium 自動草稿建立工具

使用 Playwright 自動開啟 Medium 編輯器，貼入最新 `*-medium-version.html` 的標題與內文，建立草稿。

---

## 執行流程

### 第一步：找到最新 HTML

確認 `outputs/` 下有 `*-medium-version.html`：

```bash
ls -t outputs/weekly/final/*-medium-version.html outputs/monthly/final/*-medium-version.html 2>/dev/null | head -1
```

若無結果，提示用戶先執行 `/convert-report-format`。

### 第一步半：自動生成封面圖

在執行腳本前，先確認封面圖是否存在：

```bash
ls outputs/weekly/final/*-cover.png outputs/monthly/final/*-cover.png 2>/dev/null
```

**情況 A — 封面圖已存在**：顯示路徑，直接繼續。

**情況 B — 封面圖不存在**：自動執行 `/fetch-figma-cover` 生成封面圖：

- 週報：`python3 .claude/skills/fetch-figma-cover/generate-cover.py {week-basename}`
  - `{week-basename}`：當前週報的 basename，例如 `week-1-april-2026`
  - 日期自動使用執行當天（發布日），無需傳入
- 月報：`python3 .claude/skills/fetch-figma-cover/generate-cover.py --monthly {month-basename} "{Month YYYY Report}"`

生成後確認輸出檔案存在，再繼續執行 Playwright 腳本。**禁止在未嘗試生成的情況下直接跳過封面圖。**

---

### 第二步：執行 Playwright 腳本

```bash
node .claude/skills/publish-medium/import-to-medium.js
```

**首次執行（session 不存在）**：
- 自動開啟 Chromium 到 Medium 登入頁
- 等待用戶手動完成登入
- 儲存 session 至 `~/.config/typus-medium-session.json`
- 提示用戶重新執行

**正常執行（session 存在）**：
- 載入已儲存的 session cookies
- 導航到 `https://medium.com/new-story`
- 自動填入標題，貼上內文 HTML
- 等待 Medium 自動儲存草稿
- 回傳草稿 URL

### 第三步：顯示結果

腳本執行完成後，顯示回傳的草稿 URL，例如：

```
✅ 草稿已建立！
🔗 草稿 URL：https://medium.com/p/xxxxxx/edit

📋 下一步：
  1. 開啟草稿確認內容
  2. 加 tags、選封面圖
  3. 點 Publish
  4. 發布後將 Medium 文章 URL 貼回給我，我會自動更新 X Threads
```

### 第四步：接收發布後 URL（自動觸發）

當用戶發布後將 Medium 文章 URL（格式：`https://medium.com/@TypusFinance/...`）貼回對話時，**自動執行**以下操作：

1. 根據目前對話的週報版本，找到對應的 X Threads 檔案：
   `outputs/weekly/final/week-{N}-{month}-{year}-x-threads.md`
   或 `outputs/monthly/final/{month}-{year}-x-threads.md`

2. 將檔案中的 `[Read the full report: LINK]` 替換為實際 URL（無中括號）：
   `Read the full report: {medium_url}`

3. 回報完成：
```
✅ X Threads 已更新
🔗 https://medium.com/@TypusFinance/...
📁 outputs/weekly/final/week-{N}-{month}-{year}-x-threads.md
```

**觸發條件**：用戶在 publish-medium 流程結束後，貼入任何 `https://medium.com/@TypusFinance/` 開頭的 URL。

---

## 安全性說明

- Session cookies 儲存於 `~/.config/typus-medium-session.json`（**repo 目錄外**）
- 不受 git 追蹤，不會意外上傳
- 此 JSON 含 Medium 登入憑證，請勿分享或上傳至任何地方

---

## 封面圖（可選）

若 `outputs/weekly/final/{week}-cover.png` 存在，腳本會自動將其插入為文章 body 的第一張圖（標題之後、副標題之前）。

**命名規範**：
- 檔名格式：`{week-basename}-cover.png`
- 範例：`week-3-march-2026-cover.png`
- 放置位置：`outputs/weekly/final/`

若封面圖不存在，腳本正常執行，跳過封面圖步驟。

---

## 前置條件

1. 已安裝 Node.js
2. 已安裝 Playwright：`npm install playwright` 或 `npx playwright install chromium`
3. 已執行 `/convert-report-format` 生成 `*-medium-version.html`
