# Typus 报告助手 (Claude Code 版本)

基于 Claude Code 的自动化报告生成系统，用于制作 Typus Finance 的月报和週报。

## 📁 项目结构

```
typus-report/
├── README.md                          # 项目说明（本文件）
├── QUICKSTART.md                      # 快速上手指南
├── CLAUDE.md                          # 项目配置指令
├── OPTIMIZATION_ROADMAP.md            # 优化路线图与已知问题
├── data-sources/                      # 数据源目录
│   ├── README.md                      # 数据源说明
│   ├── editorial-guidelines.md        # 编辑规范（数据呈现与叙事规则）
│   ├── typus-data/                    # 核心营运数据（TVL, Users）自动或手动更新
│   ├── weekly-references/             # 市场週报（Zerocap 等来源，自动抓取）
│   ├── monthly-history/               # 历史月报存档
│   ├── market-prices/                 # 月度价格数据（自动生成）
│   ├── sentio-data/                   # Sentio 链上数据（週报专用，自动获取）
│   ├── weekly-prices/                 # 週度价格数据（週报专用，自动生成）
│   └── weekly-history/                # 历史週报存档
├── outputs/                           # 输出目录
│   ├── monthly/                       # 月报输出
│   │   ├── draft/                     # 月报草稿
│   │   └── final/                     # 月报最终成品
│   └── weekly/                        # 週报输出
│       ├── draft/                     # 週报草稿
│       └── final/                     # 週报最终成品
└── .claude/skills/                    # 本项目 Skills（本地，优先级最高）
```

---

## 🎯 全部 Skills 一览

本项目共 10 个 Skills，分为数据抓取、月报流程、週报流程、工具类四类（`/git` 含两个子命令）。

---

### 数据自动抓取类

#### `/fetch-typus-data`
**功能**：自动从 Google Sheets 下载 Typus 核心营运数据（TVL & Users）

**用途**：替代手动更新 CSV，确保数据是最新版本

**执行内容**：
- 从公开 Google Sheets 下载 TVL 和 Users CSV
- 自动筛选必要栏位（移除地理分布、设备分布等噪音栏位）
- 整份取代本地文件（Google Sheets 是 source of truth）
- 报告行数变化与最新月份

**示例**：
```bash
/fetch-typus-data
```

---

#### `/fetch-weekly-references`
**功能**：自动从外部来源（Zerocap 等）抓取每週加密市场报告

**用途**：替代手动复制周报内容，自动精简并结构化存档

**执行内容**：
- 检测已有覆盖范围，找出缺少的週
- 抓取 Zerocap Weekly Crypto Market Wrap 文章列表
- 下载并精简每篇文章（保留所有关键数字、去除营销废话）
- 按规范命名存档（`Week_DD Mon, YYYY.md`）

**示例**：
```bash
/fetch-weekly-references
```

---

#### `/fetch-sentio-data`
**功能**：从 Sentio 平台 API 抓取週报所需的 Typus 链上数据

**用途**：週报的核心数据来源，自动执行 11 个查询

**执行内容**：
- Q1 TLP 价格走势（mTLP & iTLP-TYPUS）
- Q2 週交易量与手续费
- Q3 累积交易量快照
- Q4 每日幣种方向交易量分布
- Q5 每日交易者盈亏
- Q6 每日清算量
- Q7 每日不重复用户（DAU）
- Q8 当前持仓快照（OI）
- Q9 mTLP 资产组成（SUI/USDC 权重）
- Q10 OI 历史变化
- Q11 iTLP-TYPUS TVL
- 保存为结构化 Markdown：`data-sources/sentio-data/week-{N}-{month}-{year}.md`

**示例**：
```bash
/fetch-sentio-data
```

> **注意**：需要 Sentio API Key，存放于 `.claude/skills/fetch-sentio-data/.api-key`

---

#### `/fetch-market-prices`
**功能**：自动获取加密货币历史价格数据，支持月度和週度两种模式

**用途**：月报和週报的市场价格数据来源

**两种模式对比**：

| 参数 | 月度模式 | 週度模式 |
|------|---------|---------|
| 时间范围 | 前一个完整月份 | 指定週（週一～週日）|
| 数据间隔 | 4 小时 | 1 小时 |
| 默认幣种 | BTC, ETH, SOL, SUI, XRP | BTC, ETH, SOL, SUI |
| 输出路径 | `market-prices/{month}-{year}.md` | `weekly-prices/week-{N}-{month}-{year}.md` |

**示例**：
```bash
/fetch-market-prices          # 直接呼叫时会询问模式
```

---

### 月报流程

#### `/monthly-report-prepare`
**功能**：验证月报数据源完整性，自动补全缺失数据

**使用时机**：开始制作月报前

**执行内容**：
- 检查 Typus Data（核心营运数据）是否包含 M 和 M-1 数据
  - 若当月数据缺失，**自动触发 `/fetch-typus-data`**
- 检查 Weekly References（市场週报）是否覆盖完整月份
  - 若週报不足，**自动触发 `/fetch-weekly-references`**
- 检查 Monthly History（历史月报）是否有上月存档
- 报告数据状态和缺失项

**示例**：
```bash
/monthly-report-prepare
```

---

#### `/monthly-report-generate`
**功能**：生成完整月报、副标题、X Threads

**使用时机**：所有数据准备完成后

**执行内容**：
- 读取编辑规范（`editorial-guidelines.md`）
- 索取补充资讯（产品进度、营运事件）
- 若月度价格缺失，**自动触发 `/fetch-market-prices`**
- 整合所有数据源，生成月报初稿（按 10 点架构）
- 提供 5 个英文副标题选项
- 生成 X Threads（5 条推文）
- 保存成品到 `outputs/monthly/final/`

**示例**：
```bash
/monthly-report-generate
```

---

#### `/convert-report-format`
**功能**：将 Markdown 格式月报转换为 HTML 格式

**用途**：在 Medium 等平台发布前的格式处理

**两种模式**：
- **标准转换**：保留所有原始格式
- **Medium 优化**：移除 `<hr>` 分隔线，优化链接

**示例**：
```bash
/convert-report-format
```

---

### 週报流程

#### `/weekly-report-prepare`
**功能**：验证週报数据源、计算衍生指标、产出 Weekly Data Brief

**使用时机**：Sentio 数据抓取完成后（价格和市场参考会自动补全）

**执行内容**：
- 验证 Sentio 数据是否存在
- 若週度价格缺失，**自动触发 `/fetch-market-prices`**
- 若市场参考不足，**自动触发 `/fetch-weekly-references`**
- 自动补全缺失的历史週数据（用于 30D 绩效计算）
- 计算衍生指标（TLP 回报归因 / Alpha / 30D 绩效 / Sharpe Ratio 等）
- 标记历史趋势（连续趋势、ATH、异常值）
- **生成 30D 绩效图表**（PNG，保存至 `outputs/weekly/final/`）
- 产出结构化 Weekly Data Brief（`data-sources/sentio-data/week-{N}-{month}-{year}-brief.md`）

**示例**：
```bash
/weekly-report-prepare
```

---

#### `/weekly-report-generate`
**功能**：根据 Weekly Data Brief 生成 TLP 週报、副标题、X Threads

**使用时机**：Sentio 数据抓取完成后（Data Brief 和市场参考会自动补全）

**执行内容**：
- 读取编辑规范（`editorial-guidelines.md`）
- 若 Weekly Data Brief 缺失，**自动触发 `/weekly-report-prepare`**
- 若市场参考缺失，**自动触发 `/fetch-weekly-references`**
- 向用户收集补充资讯（市场洞见、特殊事件）
- 提议敘事方向与段落排序，等待确认
- 撰写完整 Medium 文章草稿（600-800 字，无表格）
- 用户审阅修改后产出最终版本
- 生成 5 个副标题选项和 5 条 X Threads

**示例**：
```bash
/weekly-report-generate
```

---

### 工具类

#### `/git`
**功能**：统一 git 操作，支持两个子命令，解决多 session 并行时 commit message 不完整的问题

**子命令：**

**`/git commit`** — 记录当前 session 的变更到跨 session 暂存（`pending-commits.md`）
- 分析当前 `git diff`，产生简洁中文描述
- 附加到 `.claude/skills/git/pending-commits.md`（格式：`- [HH:MM] <描述>`）
- 不执行实际 git 操作，仅作记录

**`/git push`** — 合并所有 pending 紀录 + 当前变更，推送到 GitHub
- 读取 `pending-commits.md` 中所有 session 的紀录
- 合并产生完整 commit message（或使用手动指定内容）
- 依序执行 `git add .` → `git commit` → `git push`
- Push 成功后自动清除 `pending-commits.md`

**示例**：
```bash
/git commit                    # 记录当前变更到 pending-commits
/git push                      # 合并所有紀录并推送（自动产生 commit message）
/git push 新增二月第四週週报   # 使用指定的 commit message 推送
```

---

## 🔄 完整工作流程

### 月报工作流程

```
1. /monthly-report-prepare     ← 验证数据完整性（缺失数据自动补全）
                                    ├── 自动触发 /fetch-typus-data（若数据缺失）
                                    └── 自动触发 /fetch-weekly-references（若週报不足）
2. /monthly-report-generate    ← 生成月报
                                    └── 自动触发 /fetch-market-prices（若价格缺失）
3. /convert-report-format      ← 转换为 HTML（可选）
4. /git push                   ← 推送到 GitHub（可选）
```

> 也可提前手动执行 `/fetch-typus-data`、`/fetch-weekly-references`、`/fetch-market-prices`

### 週报工作流程

```
1. /fetch-sentio-data          ← 抓取 Sentio 链上数据（唯一必须手动执行的步骤）
2. /weekly-report-prepare      ← 验证数据、计算指标、产出 Data Brief + 30D 图表
                                    ├── 自动触发 /fetch-market-prices（若价格缺失）
                                    └── 自动触发 /fetch-weekly-references（若週报不足）
3. /weekly-report-generate     ← 生成週报
                                    ├── 自动触发 /weekly-report-prepare（若 Brief 缺失）
                                    └── 自动触发 /fetch-weekly-references（若市场参考缺失）
4. /git push                   ← 推送到 GitHub（可选）
```

---

## 📊 数据格式说明

### Typus Data 格式

通过 `/fetch-typus-data` 自动获取，或手动放置 CSV 文件。

**TVL CSV 保留栏位（前 15 栏）**：
```
Milestone, Month, TVL, TVL Growth %,
Typus Perp TVL, Perp TVL Growth %,
DOV TVL, DOV TVL Growth %,
SAFU TVL, SAFU TVL Growth %,
[separator],
Accumulated Notional Volume_Perps, Notional Volume_Perps,
Accumulated TLP Fee, TLP Fee
```

**重要**：系统会忽略旧的 TVL_Total，使用新公式：
- **Total TVL** = TVL_Perps + DOV TVL + (2 × SAFU TVL)
- **Options TVL** = DOV TVL + (2 × SAFU TVL)

### 市场价格格式

- **月度**：`data-sources/market-prices/{month}-{year}.md`（4 小时间隔，BTC/ETH/SOL/SUI/XRP）
- **週度**：`data-sources/weekly-prices/week-{N}-{month}-{year}.md`（1 小时间隔，BTC/ETH/SOL/SUI）

### Sentio 链上数据格式

- **原始数据**：`data-sources/sentio-data/week-{N}-{month}-{year}.md`
- **Data Brief**：`data-sources/sentio-data/week-{N}-{month}-{year}-brief.md`
- **30D 绩效图表**：`outputs/weekly/final/week-{N}-{month}-{year}-30d-performance.png`

### Weekly References 文件命名

- **格式**：`Week_DD Mon ~ DD Mon, YYYY.md`（含完整日期范围）
- **示例**：`Week_26 Jan ~ 01 Feb, 2026.md`

---

## 🎨 月报架构（10 点）

1. **标题**：Typus [Mon] Update: [Hero Metric] + [核心叙事]
2. **TL;DR**：3-4 个 Bullet Points
3. **Market Pulse & TVL**：市场背景 + TVL 状态
4. **Performance Deep Dive**：核心指标详解
5. **User Engagement**：用户活跃度数据
6. **Product Shipped**：已上线功能
7. **Roadmap Update**：测试中 + 开发中功能
8. **Community & Ecosystem**：社群与生态系统
9. **Building Momentum**：总结与展望
10. **CTA 模块**：固定链接和结尾语

## 🗓️ 週报架构

1. **Title**：`Typus TLP Weekly Report | [Month] [DD], [YYYY]`
2. **TL;DR**：单段叙事格式（非 bullet points）
3. **Market Context**（敘事型标题）：宏观背景 + 平台交易量 + 市场表现
4. **LP Performance**（敘事型标题）：Alpha 框架 + 三因素归因（Fee / Counterparty / Basket）
5. **30-Day Performance**：累积回报 + Sharpe Ratio
6. **Trader Performance**（敘事型标题）：Realized P&L + 清算分析
7. **OI & Sentiment**（敘事型标题）：OI 趋势 + Long/Short 比例
8. **收尾段落**：主题总结 + 展望
9. **CTA**：`https://typus.finance/tlp/`

---

## 🐦 X Threads 格式（两种报告通用结构）

- 1 条引子（Intro Hook）
- 4 条带编号推文（1/4, 2/4, 3/4, 4/4）
- 简洁专业，无 emoji（Hook 例外）
- 每条 200-280 字符
- 最后一条包含 Medium 链接占位符和 CTA

---

## ⚙️ Skills 安装位置

Skills 安装在本项目目录下（本地 Skills，优先级高于全局 Skills）：

```
.claude/skills/
├── fetch-typus-data/
│   └── SKILL.md
├── fetch-weekly-references/
│   └── SKILL.md
├── fetch-sentio-data/
│   ├── SKILL.md
│   ├── SENTIO-SCHEMA.md
│   ├── .api-key           # Sentio API Key（已加入 .gitignore）
│   └── queries/           # 各 Query 定义文件
├── fetch-market-prices/
│   └── SKILL.md
├── monthly-report-prepare/
│   └── SKILL.md
├── monthly-report-generate/
│   └── SKILL.md
├── convert-report-format/
│   └── SKILL.md
├── weekly-report-prepare/
│   └── SKILL.md
├── weekly-report-generate/
│   └── SKILL.md
└── git/
    ├── SKILL.md
    └── pending-commits.md     # 跨 session 暂存（已加入 .gitignore）
```

如需修改 Skills 行为，编辑对应目录下的 `SKILL.md` 文件，保存后立即生效。

---

## 🔧 常见问题

### Q1: 如何设置 Sentio API Key？

将 API Key 写入以下文件（一行）：
```
.claude/skills/fetch-sentio-data/.api-key
```
此文件已加入 `.gitignore`，不会被上传。

### Q2: 如果价格获取失败怎么办？

可以手动提供价格数据，或跳过并在生成时手动输入。

### Q3: 週报和月报可以同时进行吗？

可以，两套工作流程完全独立，数据目录不重叠。

### Q4: 如何修改 Skills 的行为？

编辑 `.claude/skills/` 中对应 `SKILL.md` 文件，保存后立即生效。

### Q5: Weekly References 的日期规则是什么？

Zerocap 文章标题日期减 7 天 = 实际涵盖週的週一。例如标题 "2 February 2026" → 实际涵盖 1 月 26 日（週一）至 2 月 1 日（週日）。

文件命名格式为完整日期范围：`Week_26 Jan ~ 01 Feb, 2026.md`

---

## 📚 参考文档

- **快速上手**：`QUICKSTART.md`
- **週报开发记录**：`WEEKLY-REPORT-ROADMAP.md`
- **数据源说明**：`data-sources/README.md`
- **原始 SOP（月报）**：`Typus 月報助手使用手冊 (SOP) Google Gemini.pdf`
- **原始 SOP（週报）**：`Typus TLP 週報助手使用手冊 Gemini.pdf`

---

## 📄 版本历史

- **v2.2** (2026-03-04): 統一 git 操作
  - 新增 `/git`：取代 `/push`，支援 `/git commit`（跨 session 暫存）和 `/git push`（合併所有紀錄推送）
  - 解決多 session 並行時 commit message 不完整的問題

- **v2.1** (2026-03-04): 自动化强化 + 工具补全
  - 新增 `/push`（已由 `/git` 取代）：一键推送本地变更到 GitHub，支持自动/手动 commit message
  - `monthly-report-prepare` 新增自动触发 `fetch-typus-data` 和 `fetch-weekly-references`
  - `monthly-report-generate` 新增自动触发 `fetch-market-prices`
  - `weekly-report-prepare` 新增自动触发价格/市场参考抓取、生成 30D 绩效图表（PNG）
  - `weekly-report-generate` 新增自动触发 `weekly-report-prepare` 和 `fetch-weekly-references`
  - `fetch-sentio-data` 新增 Q11（iTLP-TYPUS TVL）
  - 新增 `data-sources/editorial-guidelines.md`（编辑规范）
  - Weekly References 文件命名更新为完整日期范围格式
  - 输出目录调整：`outputs/drafts/` + `outputs/final/` → `outputs/monthly/draft/` + `outputs/monthly/final/`

- **v2.0** (2026-02-28): 新增週报功能
  - 新增 `fetch-sentio-data`：从 Sentio API 抓取链上数据（10 个 Query）
  - 新增 `weekly-report-prepare`：週报数据验证 + 指标计算 + Data Brief 生成
  - 新增 `weekly-report-generate`：TLP 週报 Medium 文章 + 副标题 + X Threads
  - 新增 `fetch-typus-data`：自动从 Google Sheets 下载 TVL & Users CSV
  - 新增 `fetch-weekly-references`：自动抓取 Zerocap 等来源的週报
  - 更新 `fetch-market-prices`：支持月度/週度双模式，新增 SUI/XRP
  - 新增 `convert-report-format`：Markdown → HTML 格式转换
  - 新增数据目录：`sentio-data/`、`weekly-prices/`、`weekly-history/`
  - 新增输出目录：`outputs/weekly/`

- **v1.0** (2026-02-03): 初始版本，从 Google Gemini 迁移到 Claude Code
  - 三个核心月报 Skills
  - 实现自动价格获取
  - 完整月报工作流程

---

**祝您使用愉快！**
