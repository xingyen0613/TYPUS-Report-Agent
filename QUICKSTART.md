# Typus 报告助手 - 快速上手指南

## 📋 命令速查表

| 命令 | 用途 | 适用报告 |
|------|------|---------|
| `/fetch-typus-data` | 从 Google Sheets 自动更新 TVL & Users CSV | 月报 |
| `/fetch-weekly-references` | 自动抓取 Zerocap 等来源的市场週报 | 月报 / 週报 |
| `/fetch-sentio-data` | 从 Sentio API 抓取链上数据 | 週报 |
| `/fetch-market-prices` | 获取加密货币历史价格（月度或週度） | 月报 / 週报 |
| `/monthly-report-prepare` | 验证月报数据完整性 | 月报 |
| `/monthly-report-generate` | 生成月报 + 副标题 + X Threads | 月报 |
| `/convert-report-format` | 将月报转换为 HTML 格式 | 月报 |
| `/weekly-report-prepare` | 验证週报数据、计算指标、产出 Data Brief | 週报 |
| `/weekly-report-generate` | 生成週报 + 副标题 + X Threads | 週报 |
| `/git commit` | 分析当前变更并记录到跨 session 暂存（pending-commits） | 通用 |
| `/git push` | 合并所有 pending 紀录推送到 GitHub（自动或手动 commit message） | 通用 |

---

## 月报工作流程

### 步骤 1：验证数据（自动补全）

```bash
/monthly-report-prepare
```

系统自动检查所有数据源，**缺什么就自动抓什么**：
- Typus Data 缺失 → 自动触发 `/fetch-typus-data`
- Weekly References 不足 → 自动触发 `/fetch-weekly-references`

预期输出（数据齐全时）：
```
✅ Typus Data — 最新月份：[月份]，TVL + Users 完整
✅ Weekly References — 找到 [N] 个週报文件
✅ Monthly History — 上月月报存在
```

> 也可提前手动执行 `/fetch-typus-data` 或 `/fetch-weekly-references`

---

### 步骤 2：生成月报

```bash
/monthly-report-generate
```

AI 会询问：
- **产品进度**：Shipped / In Final Testing / In Active Development
- **营运事件**：合作、活动、社群事件

若月度价格未准备，系统**自动抓取**（或可提前执行 `/fetch-market-prices`）。

回复补充资讯后，AI 输出：
1. **月报完整版**（Markdown）→ `outputs/monthly/draft/[month]-[year]-report-draft.md`
2. **5 个副标题选项**（≤140 字符）
3. **X Threads**（5 条推文）

选择副标题后，定稿保存至 `outputs/monthly/final/`。

---

### 步骤 3（可选）：转换格式

```bash
/convert-report-format
```

将 Markdown 月报转换为 HTML，适合在 Medium 发布。

---

## 週报工作流程

### 步骤 1：获取链上数据（唯一必须手动执行的步骤）

```bash
/fetch-sentio-data
```

系统自动取前一个完整週（例如：今天週二，则抓取上週一至週日的数据）。执行 11 个 Sentio 查询，保存至 `data-sources/sentio-data/week-{N}-{month}-{year}.md`。

> **前置条件**：需要 Sentio API Key，存放于 `.claude/skills/fetch-sentio-data/.api-key`

---

### 步骤 2：准备 Data Brief（自动补全）

```bash
/weekly-report-prepare
```

系统自动补全所有缺失数据：
- 週度价格缺失 → 自动触发 `/fetch-market-prices`
- 市场参考不足 → 自动触发 `/fetch-weekly-references`
- 历史週数据缺失 → 自动补抓（用于 30D 绩效计算）

然后计算并产出：
- TLP 回报归因（Alpha / Fee / Counterparty / Basket）
- 30D 绩效 + Sharpe Ratio
- **30D 绩效图表**（PNG）→ `outputs/weekly/final/week-[N]-[month]-[year]-30d-performance.png`
- 结构化 Weekly Data Brief → `data-sources/sentio-data/week-[N]-[month]-[year]-brief.md`

如数据有误，可直接告知 AI 修正。

---

### 步骤 3：生成週报

```bash
/weekly-report-generate
```

AI 会：
1. 自动读取 Data Brief 和市场参考（缺失时自动补全）
2. 询问补充资讯（市场洞见、特殊事件）
3. 提议敘事方向（看多/看空/中性）和段落排序，**等待你确认**
4. 撰写草稿（600-800 字 Medium 文章，无表格）→ `outputs/weekly/draft/...`
5. 等待你审阅，根据反馈修改
6. 确认后产出最终版本 + 副标题 + X Threads → `outputs/weekly/final/...`

---

## ⚠️ 常见问题

### Q: Sentio API Key 如何设置？

将 API Key 写入文件（一行）：
```
.claude/skills/fetch-sentio-data/.api-key
```
此文件已加入 `.gitignore`，不会被上传。

### Q: 价格获取失败怎么办？

可手动提供价格数据，格式示例：
```
W1 (1/1-1/7): BTC $95k → $97k, ETH $3.3k → $3.5k, SOL $210 → $225, SUI $4.1 → $4.3
```

### Q: Weekly References 的日期规则是什么？

Zerocap 文章标题日期减 7 天 = 实际涵盖週的週一。
- 文章 "2 February 2026" → 实际涵盖 1/26（週一）至 2/1（週日）
- 对应文件名：`Week_26 Jan ~ 01 Feb, 2026.md`（完整日期范围格式）

### Q: 週报和月报的数据目录分开吗？

是的，完全独立：
- 月报价格 → `data-sources/market-prices/`
- 週报价格 → `data-sources/weekly-prices/`
- 週报链上数据 → `data-sources/sentio-data/`
- 週报历史存档 → `data-sources/weekly-history/`

### Q: 如何修改 Skills 行为？

编辑 `.claude/skills/[skill-name]/SKILL.md`，保存后立即生效。

---

## 📚 更多资源

- **完整文档**：`README.md`
- **週报开发记录**：`WEEKLY-REPORT-ROADMAP.md`
- **数据源说明**：`data-sources/README.md`
