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

**若未指定**：自動在 `outputs/` 下尋找最新的月報或週報（檔名含 `monthly-report.md` 或 `weekly-report.md`，取修改時間最新者）。確認後直接執行，無需詢問。

### 第二步：決定轉換模式

- **預設**：Medium 優化模式
- **例外**：用戶明確說「標準」或「standard」時，改用標準模式

### 第三步：執行轉換

使用以下 Python 腳本轉換（輸出完整 HTML，含 `<html>`/`<head>`/`<body>`）：

```python
import re, os

MONTHS = {
    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12
}

GITHUB_PAGES_BASE = 'https://xingyen0613.github.io/TYPUS-Report-Agent/'
REPO_ROOT = '/Users/yen/claude/typus-report'

def process_inline(text, mode):
    text = text.replace('&', '&amp;')
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    if mode == 'medium':
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)
        text = re.sub(r'(?<!["\(])(https?://[^\s<\)]+)', r'<a href="\1">\1</a>', text)
    return text

def convert_body(md_content, mode='medium'):
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

def get_github_pages_url(output_path):
    rel = os.path.relpath(output_path, REPO_ROOT)
    return GITHUB_PAGES_BASE + rel.replace(os.sep, '/')

def get_iso_date(filename):
    base = os.path.basename(filename).replace('.html', '')
    parts = base.split('-')
    year = None
    month = None
    for i, p in enumerate(parts):
        if p in MONTHS:
            month = MONTHS[p]
            if i+1 < len(parts) and parts[i+1].isdigit() and len(parts[i+1]) == 4:
                year = int(parts[i+1])
    if year and month:
        return f'{year:04d}-{month:02d}-01T00:00:00Z'
    return ''

def extract_meta(html_body):
    title = ''
    desc = ''
    m = re.search(r'<h1>([^<]+)</h1>', html_body)
    if m: title = m.group(1)
    m = re.search(r'<h2>([^<]+)</h2>', html_body)
    if m: desc = m.group(1)
    return title, desc

def replace_30d_chart(html_content, output_dir, output_filename):
    try:
        png_files = [f for f in os.listdir(output_dir) if f.endswith('-30d-performance.png')]
    except Exception:
        return html_content
    if not png_files:
        return html_content
    base = output_filename.replace('-medium-version.html', '').replace('.html', '')
    matching = [f for f in png_files if f.startswith(base)]
    if not matching:
        matching = png_files
    png_file = sorted(matching)[0]
    figure = f'<figure><img src="./{png_file}" alt="30-Day Performance Comparison"></figure>'
    return html_content.replace('<p>[Image: 30-Day Comparison Chart]</p>', figure)

def build_full_html(body, og_title, og_desc, og_url, og_date):
    title_esc = og_title.replace('"', '&quot;')
    desc_esc = og_desc.replace('"', '&quot;')
    head = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta property="og:title" content="{title_esc}">
<meta property="og:description" content="{desc_esc}">
<meta property="og:type" content="article">
<meta property="og:url" content="{og_url}">
<meta property="article:published_time" content="{og_date}">
</head>
<body>
'''
    return head + body + '\n</body>\n</html>'

# --- main ---
# 假設：input_path、output_path、mode 已由上下文決定
body = convert_body(md_content, mode)
og_title, og_desc = extract_meta(body)
og_url = get_github_pages_url(output_path)
og_date = get_iso_date(output_path)

full_html = build_full_html(body, og_title, og_desc, og_url, og_date)

# 30D PNG 替換（週報專用）
output_dir = os.path.dirname(output_path)
output_filename = os.path.basename(output_path)
full_html = replace_30d_chart(full_html, output_dir, output_filename)

with open(output_path, 'w') as f:
    f.write(full_html)
```

### 第四步：輸出命名規則

| 模式 | 輸出檔名 |
|------|----------|
| Medium（預設） | `{basename}-medium-version.html`（去掉 `-monthly-report` 或 `-weekly-report` 後綴）<br>例：`february-2026-medium-version.html`、`week-1-march-2026-medium-version.html` |
| Standard | `{basename}.html`<br>例：`february-2026-monthly-report.html` |

**保存位置**：與來源檔案相同目錄。

### 第五步：完成報告

輸出簡潔的完成訊息，包含 GitHub Pages URL：

```
✅ HTML 轉換完成（Medium 優化模式）

📁 輸出：outputs/weekly/final/week-1-march-2026-medium-version.html
📊 H1: 1 | H2: 8 | H3: 10 | 段落: 15 | 列表項: 15 | 大小: ~11.6 KB
🖼️  30D 圖片：已嵌入 week-1-march-2026-30d-performance.png（或「無 PNG，佔位符保留」）

🌐 GitHub Pages URL（push 後可用）：
https://xingyen0613.github.io/TYPUS-Report-Agent/outputs/weekly/final/week-1-march-2026-medium-version.html

📋 下一步：/git push → 貼 URL 到 https://medium.com/p/import
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
| `[Image: 30-Day Comparison Chart]` | `<figure><img>` (若有 PNG) | 保留原格式 |
