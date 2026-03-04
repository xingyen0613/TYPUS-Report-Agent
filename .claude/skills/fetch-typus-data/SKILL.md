---
name: fetch-typus-data
description: 自動從 Google Sheets 抓取 Typus Data (TVL 和 Users CSV)，儲存至 data-sources/typus-data/
user-invocable: true
allowed-tools: Read, Write, Glob, Bash
---

# Typus Data 自動獲取（TVL & Users）

你是 Typus Finance 報告助手的數據獲取模組。你的任務是從 Google Sheets 下載最新的 TVL 和 Users 數據，篩選必要欄位後儲存為 CSV 檔案。

## 資料來源

```
Google Sheet: https://docs.google.com/spreadsheets/d/1xT7I20aOOIwvwNopg17iDpiATEGZNPvB0QoIFXPUvLk
存取方式: 公開連結 (gviz/tq endpoint)
策略: 每次整份取代 CSV（資料僅 ~30 行，Google Sheets 為 source of truth）
```

**下載 URL：**
- TVL: `https://docs.google.com/spreadsheets/d/1xT7I20aOOIwvwNopg17iDpiATEGZNPvB0QoIFXPUvLk/gviz/tq?tqx=out:csv&sheet=TVL`
- Users: `https://docs.google.com/spreadsheets/d/1xT7I20aOOIwvwNopg17iDpiATEGZNPvB0QoIFXPUvLk/gviz/tq?tqx=out:csv&sheet=Users`

---

## 執行流程

### Step 1 — 讀取現有 CSV

用 Read 讀取現有檔案，記錄當前狀態：
- `data-sources/typus-data/Typus Data - TVL.csv`
- `data-sources/typus-data/Typus Data - Users.csv`

記錄：
- 各檔案的行數
- 最後一行的 Month 欄位值（最新月份）

### Step 2 — 用 Python 下載並處理新資料

透過 `Bash(python3 ...)` 執行 Python 腳本，一次處理兩個 CSV。

**Python 腳本需求：**

```python
import urllib.request
import csv
import io
import sys

SHEET_ID = "1xT7I20aOOIwvwNopg17iDpiATEGZNPvB0QoIFXPUvLk"
BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="

# 各 sheet 的設定：(sheet名稱, 保留欄數, 輸出檔名)
SHEETS = [
    ("TVL", 15, "data-sources/typus-data/Typus Data - TVL.csv"),
    ("Users", 16, "data-sources/typus-data/Typus Data - Users.csv"),
]
```

**處理邏輯：**
1. 用 `urllib.request.urlopen()` 下載 CSV
2. 用 `csv.reader` 解析
3. **TVL:** 只保留前 15 欄（Milestone 到 TLP Fee），去除尾部空欄
4. **Users:** 只保留前 16 欄（Milestone 到 MAU % - Typus v2），去除地理分佈和設備分佈欄位
5. 用 `csv.writer` 寫回檔案，保持標準 CSV 格式
6. 將結果輸出到 stdout 供後續比較

**欄位篩選明細：**

TVL 保留欄位（前 15 欄）：
```
Milestone, Month, TVL, TVL Growth %, Typus Perp TVL, Perp TVL Growth %,
DOV TVL, DOV TVL Growth %, SAFU TVL, SAFU TVL Growth %, [separator],
Accumulated Notional Volume_Perps, Notional Volume_Perps, Accumulated TLP Fee, TLP Fee
```

Users 保留欄位（前 16 欄）：
```
Milestone, Month, Web Traffic-Total Visitors, Web Traffic-New Visitors,
Total Users, Total Users - Typus Perp, Total Users - Typus v2,
Total New Users, New Users - Typus Perp, New Users - Typus v2,
New User %, User Growth,
MAU - Typus Perp, MAU % - Typus Perp, MAU - Typus v2, MAU % - Typus v2
```

移除的欄位：地理分佈（US, Japan, Taiwan... 等 15+ 國家及百分比）、設備分佈（Desktop, Mobile, Tablet 及百分比）

### Step 3 — 寫入檔案

用 Write 工具將處理後的 CSV 內容寫入對應檔案。

### Step 4 — 比較變更

比較更新前後的差異：
- 行數變化（新增了幾行）
- 最新月份是否改變
- 任何數據值的變化

### Step 5 — 回報完成

顯示更新摘要：

```
Typus Data 已更新：

TVL CSV:
  - 行數: [舊] → [新]
  - 最新月份: [月份]
  - 欄位數: 15 ✓
  - 變更: [新增 N 行 / 數據已更新 / 無變更]

Users CSV:
  - 行數: [舊] → [新]
  - 最新月份: [月份]
  - 欄位數: 16 ✓
  - 變更: [新增 N 行 / 數據已更新 / 無變更]

下一步：/monthly-report-prepare
```

---

## 錯誤處理

- **Google Sheets 無法連線** → 回報錯誤，保留現有 CSV 不動
- **CSV 解析失敗** → 回報錯誤，不寫入
- **資料為空**（下載後無資料行）→ 警告並中止，不覆蓋現有檔案
- **欄位數不符預期** → 警告使用者，顯示實際欄位數和標題列供確認

---

## 注意事項

- 每次執行都是整份取代（Google Sheets 是 source of truth）
- 不要修改 CSV 中的任何數據值，只做欄位篩選
- 下載失敗時絕對不能覆蓋現有檔案
- Python 腳本只使用標準庫（urllib, csv, io, sys），不需額外安裝套件
