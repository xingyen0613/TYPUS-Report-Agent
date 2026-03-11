---
name: publish-medium
description: 顯示最新 HTML 的 GitHub Pages URL，供貼到 Medium import 頁面建立草稿
user-invocable: true
allowed-tools: Glob, Bash
---

# Medium Import 輔助工具

找到最新的 `*-medium-version.html`，計算對應的 GitHub Pages URL，供用戶一鍵開啟 Medium import 建立草稿。

---

## 執行流程

### 第一步：找到最新 HTML

搜尋 `outputs/` 下所有 `*-medium-version.html`，取修改時間最新者。

```bash
ls -t outputs/weekly/final/*-medium-version.html outputs/monthly/final/*-medium-version.html 2>/dev/null | head -1
```

### 第二步：計算 GitHub Pages URL

URL 格式：
```
https://xingyen0613.github.io/TYPUS-Report-Agent/{相對路徑}
```

例：
- `outputs/weekly/final/week-1-march-2026-medium-version.html`
  → `https://xingyen0613.github.io/TYPUS-Report-Agent/outputs/weekly/final/week-1-march-2026-medium-version.html`
- `outputs/monthly/final/february-2026-medium-version.html`
  → `https://xingyen0613.github.io/TYPUS-Report-Agent/outputs/monthly/final/february-2026-medium-version.html`

### 第三步：顯示結果

輸出以下訊息（直接顯示，供用戶複製）：

```
📄 最新 HTML：outputs/weekly/final/week-1-march-2026-medium-version.html

🌐 GitHub Pages URL：
https://xingyen0613.github.io/TYPUS-Report-Agent/outputs/weekly/final/week-1-march-2026-medium-version.html

📋 Medium Import 步驟：
1. 確認已執行 /git push（GitHub Pages 部署需 ~1 分鐘）
2. 開啟：https://medium.com/p/import
3. 貼上上方 URL → 點 Import
4. Import 後為草稿，手動完成：加 tags、選封面圖、點 Publish

💡 Tips：
- Import 自動設定 canonical URL，保護 SEO ✅
- 若圖片未顯示，等待 GitHub Pages 部署完成後再 import
```

---

## 前置條件

執行此 skill 前，請確認：
1. 已執行 `/convert-report-format` 生成 HTML
2. 已執行 `/git push` 將 HTML 推上 GitHub（Pages 部署約需 1 分鐘）
