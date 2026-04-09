---
name: fetch-figma-cover
description: 本地生成 Weekly/Monthly 封面圖（不需開啟 Figma），供 publish-medium 自動插入
user-invocable: true
allowed-tools: Bash
---

# 封面圖生成工具

使用 `generate-cover.py` 本地生成封面 PNG，只需提供參數，完全不需開啟 Figma。

---

## Weekly 封面

```bash
python3 .claude/skills/fetch-figma-cover/generate-cover.py <week-basename> "<date>"
```

- `<date>`：報告週期第一天（週一），格式 `Mar. 23, 2026`
- 輸出：`outputs/weekly/final/{week-basename}-cover.png`

範例：
```bash
python3 .claude/skills/fetch-figma-cover/generate-cover.py week-4-march-2026 "Mar. 23, 2026"
```

---

## Monthly 封面

```bash
python3 .claude/skills/fetch-figma-cover/generate-cover.py --monthly <month-basename> "<title>" "<date>"
```

- `<title>`：月報標題，格式 `Mar 2026 Report`（報告內容月份）
- `<date>`：發布當日日期，格式 `Apr 9, 2026`（**可省略，省略時自動使用執行當天日期**）
- 輸出：`outputs/monthly/final/{month-basename}-cover.png`

範例：
```bash
# 省略日期 → 自動用今天（推薦）
python3 .claude/skills/fetch-figma-cover/generate-cover.py --monthly march-2026 "Mar 2026 Report"

# 或手動指定日期
python3 .claude/skills/fetch-figma-cover/generate-cover.py --monthly march-2026 "Mar 2026 Report" "Apr 9, 2026"
```

---

## 初始設定（僅需執行一次）

首次使用前需要執行 setup，從 Figma API 下載 calendar icon 並建立兩份 base template：

```bash
python3 .claude/skills/fetch-figma-cover/generate-cover.py --setup
```

需要 `FIGMA_API_KEY`（來自 `~/.claude/settings.json` 的 MCP env），**僅 setup 時需要，之後完全不需 Figma**。

---

## 後續步驟

封面圖儲存後，直接執行 `/publish-medium`，腳本會自動偵測並插入封面為文章首圖。
