# Query 12: Daily Total Volume（每日總交易量）

**用途**：獲取每日平台總交易量（USD），用於生成 Daily Volume 趨勢圖（7根柱狀圖）。

**API Endpoint**：`https://api.sentio.xyz/v1/insights/typus/typus_perp/query`（Metrics endpoint）

---

## 請求 Payload

```json
{
  "version": 9,
  "timeRange": {
    "start": "{{UNIX_START}}",
    "end": "{{UNIX_END}}",
    "step": 86400,
    "timezone": "Asia/Taipei"
  },
  "limit": 20,
  "queries": [
    {
      "metricsQuery": {
        "query": "trading_volume_usd",
        "alias": "",
        "id": "a",
        "labelSelector": {},
        "aggregate": {
          "op": "SUM",
          "grouping": []
        },
        "functions": [
          {
            "name": "rollup_delta",
            "arguments": [
              {
                "durationValue": {
                  "value": 1,
                  "unit": "d"
                }
              }
            ]
          }
        ],
        "color": "",
        "disabled": false
      },
      "dataSource": "METRICS",
      "sourceName": ""
    }
  ],
  "formulas": [],
  "cachePolicy": {
    "noCache": false,
    "cacheTtlSecs": 2592000,
    "cacheRefreshTtlSecs": 172800
  }
}
```

### 時間參數格式

Metrics endpoint，替換 `timeRange.start/end`：
```python
payload["timeRange"]["start"] = str(unix_start)
payload["timeRange"]["end"]   = str(unix_end)
```

---

## 回傳格式

Metrics 標準格式，`results[0].matrix.samples[0].values[]` 為 `[timestamp, value]` 陣列，每天一筆（step=86400）。

---

## 在 sentio-data MD 的輸出格式

```markdown
## 12. Daily Total Volume（每日總交易量）

| Day | Date | Volume (USD) |
|-----|------|--------------|
| Mon | 2026-02-02 | $1,234,567.00 |
| Tue | 2026-02-03 | $987,654.00 |
| Wed | 2026-02-04 | $1,100,000.00 |
| Thu | 2026-02-05 | $800,000.00 |
| Fri | 2026-02-06 | $950,000.00 |
| Sat | 2026-02-07 | $600,000.00 |
| Sun | 2026-02-08 | $750,000.00 |

**週總交易量**: $6,421,221.00
```

---

## 注意事項

- `rollup_delta` 計算每個 step 區間內的增量，所以每筆是當天新增的交易量（非累積）
- `timezone: "Asia/Taipei"` 使 step 按台北時間對齊（UTC+8 00:00 切換）
- 回傳 7 筆資料（週一到週日各一筆）
- timestamp 對應的是區間**結束**時間（即每天 00:00 台北時間），換算日期時需注意
