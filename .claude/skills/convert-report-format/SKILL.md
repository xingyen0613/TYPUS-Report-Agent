---
name: convert-report-format
description: Convert Typus monthly report from Markdown to HTML format (Standard or Medium-optimized)
user-invocable: true
allowed-tools: Read, Write, Bash, Glob
---

# 月報格式轉換工具

將 Markdown 月報轉為 HTML，預設使用 **Medium 優化模式**。

---

## 執行流程

### 第一步：確認輸入檔案

**若用戶有指定檔案**：直接使用該路徑。

**若未指定**：自動在 `outputs/monthly/final/` 尋找最新的月報（檔名含 `monthly-report.md`，取修改時間最新者）。確認後直接執行，無需詢問。

### 第二步：決定轉換模式

- **預設**：Medium 優化模式
- **例外**：用戶明確說「標準」或「standard」時，改用標準模式

### 第三步：執行轉換

使用以下 Python 腳本轉換：

```python
import re

def process_inline(text, mode):
    text = text.replace('&', '&amp;')
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    if mode == 'medium':
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)
        text = re.sub(r'(?<!["\(])(https?://[^\s<\)]+)', r'<a href="\1">\1</a>', text)
    return text

def convert(md_content, mode='medium'):
    lines = md_content.split('\n')
    html = []
    in_list = False
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.strip() == '---':
            if in_list: html.append('</ul>'); in_list = False
            if mode == 'standard': html.append('<hr>')
            i += 1; continue

        if re.match(r'^# (?!#)', line):
            if in_list: html.append('</ul>'); in_list = False
            html.append(f'<h1>{process_inline(line[2:], mode)}</h1>')
            i += 1; continue

        if line.startswith('### '):
            if in_list: html.append('</ul>'); in_list = False
            html.append(f'<h3>{process_inline(line[4:], mode)}</h3>')
            i += 1; continue

        if line.startswith('## '):
            if in_list: html.append('</ul>'); in_list = False
            html.append(f'<h2>{process_inline(line[3:], mode)}</h2>')
            i += 1; continue

        if line.startswith('- ') or line.startswith('* '):
            if not in_list: html.append('<ul>'); in_list = True
            html.append(f'<li>{process_inline(line[2:], mode)}</li>')
            i += 1; continue

        if in_list and line.strip() and not (line.startswith('- ') or line.startswith('* ')):
            html.append('</ul>'); in_list = False

        if not line.strip():
            i += 1; continue

        content = process_inline(line, mode)
        if mode == 'medium':
            m = re.match(r'^<strong>([^<]+)</strong>$', content)
            if m:
                html.append(f'<h3>{m.group(1)}</h3>')
                i += 1; continue
        html.append(f'<p>{content}</p>')
        i += 1

    if in_list: html.append('</ul>')
    return '\n'.join(html)
```

### 第四步：輸出命名規則

| 模式 | 輸出檔名 |
|------|----------|
| Medium（預設） | `{basename}-medium-version.html`（去掉 `-monthly-report` 後綴）<br>例：`february-2026-medium-version.html` |
| Standard | `{basename}.html`<br>例：`february-2026-monthly-report.html` |

**保存位置**：與來源檔案相同目錄。

### 第五步：完成報告

輸出簡潔的完成訊息：

```
✅ HTML 轉換完成（Medium 優化模式）

📁 輸出：outputs/final/february-2026-medium-version.html
📊 H1: 1 | H2: 8 | H3: 10 | 段落: 15 | 列表項: 15 | 大小: ~11.6 KB

📋 Medium 發布：全選複製 HTML 內容 → Medium 編輯器 → Cmd+Shift+V 貼上
```

---

## 轉換規則

| Markdown | Medium HTML | Standard HTML |
|----------|-------------|---------------|
| `# H1` | `<h1>` | `<h1>` |
| `## H2` | `<h2>` | `<h2>` |
| `### H3` | `<h3>` | `<h3>` |
| `**bold**` | `<strong>` | `<strong>` |
| `*italic*` | `<em>` | `<em>` |
| `- item` | `<ul><li>` | `<ul><li>` |
| `---` | 移除 | `<hr>` |
| `[text](url)` | `<a href>` | 保留原格式 |
| 純 URL | `<a href>` | 保留原格式 |
| 獨立 `**粗體**` 行 | `<h3>` | `<strong>` |
