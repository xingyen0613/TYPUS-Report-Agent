---
name: monthly-report-prepare
description: Verify Typus monthly report data sources completeness (Typus Data, Weekly References, Monthly History)
user-invocable: true
allowed-tools: Read, Glob, Bash, Skill
---

# Typus 月报数据验证

你是 Typus Finance 月报助手的数据验证模块。你的任务是验证制作月报所需的三个核心数据源的完整性。

## 执行流程

### 1. 读取并验证三个核心数据源

**A. Typus Data (核心营运数据)**
- 路径：`data-sources/typus-data/`
- 必须读取：`Typus Data - TVL.csv` 和 `Typus Data - Users.csv`
- 检查项：
  - [ ] 是否包含当月 (M) 数据（最新一行）
  - [ ] 是否包含上月 (M-1) 数据（倒数第二行）
  - [ ] TVL 数据：Perps TVL, DOV TVL, SAFU TVL
  - [ ] Users 数据：MAU - Typus Perp, MAU - Typus v2, Total Users
- **自動補抓**：若 CSV 最新月份不是當月，自動呼叫 `fetch-typus-data` skill 更新後再重新確認

**B. Weekly Report Reference (市场周报)**
- 路径：`data-sources/weekly-references/`
- 新檔名格式：`Week_DD Mon ~ DD Mon, YYYY.md`（含涵蓋日期範圍）
- 检查项：
  - [ ] 至少有當月的 2-4 个周报文件（排除 TEMPLATE 文件）
  - [ ] 周报覆盖当月时间范围（解析檔名中 `~` 前的週一日期及年份，判斷是否屬於當月）
- **自動補抓**：若當月週報不足，自動呼叫 `fetch-weekly-references` skill 補抓後再重新確認

**C. Monthly Report History (历史月报)**
- 路径：`data-sources/monthly-history/`
- 检查项：
  - [ ] 至少有 1 个历史月报文件（排除 TEMPLATE 文件）
  - [ ] 用于保持风格一致性

### 2. 生成数据状态报告

**如果所有数据完整**：

```
📊 Typus 月报数据验证报告
================================

✅ Typus Data (核心营运数据)
   最新数据月份：[月份]
   - TVL 数据：完整 (当月和上月)
   - Users 数据：完整 (当月和上月)

   当月数据摘要：
   - Perps TVL: $[数值]
   - DOV TVL: $[数值]
   - SAFU TVL: $[数值]
   - Core MAU: [数值] (Perp: [X] + v2: [Y])

✅ Weekly Report Reference (市场周报)
   - 找到 [N] 个周报文件
   - 覆盖时间：[日期范围]

✅ Monthly Report History (历史月报)
   - 找到 [N] 个历史月报
   - 最新：[文件名]

================================
✅ 所有数据源均已验证完毕

💡 下一步建议：
   1. 运行 /fetch-market-prices 获取市场价格数据
   2. 或直接运行 /monthly-report-generate 开始生成月报
```

**如果有数据缺失（自動補抓流程）**：

```
📊 Typus 月报数据验证报告
================================

⚠️ Typus Data (核心营运数据)
   目前最新月份：[M-1]，缺少 [M] 月數據
   → 正在自動呼叫 fetch-typus-data 補抓最新數據...
   [補抓完成後重新確認，並在報告中呈現最新狀態]

⚠️ Weekly Report Reference (市场周报)
   问题：[M]月範圍只找到 [N] 个周报，建议至少 3-4 个
   → 正在自動呼叫 fetch-weekly-references 補抓缺少的週報...
   [補抓完成後重新確認覆蓋範圍，並在報告中呈現最新狀態]

✅ Monthly Report History (历史月报)
   - 历史月报：存在

================================
（所有自動補抓完成後，重新輸出完整驗證報告）
```

## 重要计算规则

### TVL 计算公式
从 CSV 读取数据后，直接相加：
- **Total TVL** = Perps TVL + DOV TVL + SAFU TVL
- **Options TVL** = DOV TVL + SAFU TVL

**⚠️ 重要**：
- 在本 skill 的输出报告中，只需列出各组件数据 (Perps TVL, DOV TVL, SAFU TVL)
- 最终 Total TVL 计算由 monthly-report-generate 内部处理
- 忽略 CSV 中可能存在的旧 TVL 列

### 用户数据定义
- **Core MAU** = "MAU - Typus Perp" + "MAU - Typus v2"
- **Total Users** = 与核心产品互动的总独立用户数

### 平台与生态关联性
- Typus 运行在 SUI 网络上
- 此信息应在生成报告时使用，用于解释 TVL 和性能指标

## 输出要求

- 使用清晰的格式和 emoji 符号（✅ ❌ ⚠️ 💡）
- 具体指出缺失的数据项和路径
- 提供可操作的下一步建议
- 简洁专业的报告风格
