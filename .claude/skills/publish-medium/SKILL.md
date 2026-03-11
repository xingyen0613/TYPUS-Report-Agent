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
```

---

## 安全性說明

- Session cookies 儲存於 `~/.config/typus-medium-session.json`（**repo 目錄外**）
- 不受 git 追蹤，不會意外上傳
- 此 JSON 含 Medium 登入憑證，請勿分享或上傳至任何地方

---

## 前置條件

1. 已安裝 Node.js
2. 已安裝 Playwright：`npm install playwright` 或 `npx playwright install chromium`
3. 已執行 `/convert-report-format` 生成 `*-medium-version.html`
