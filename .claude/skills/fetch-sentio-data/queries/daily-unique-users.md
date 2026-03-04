# Query 7: Daily Unique Users（每日不重複用戶數）

**用途**：獲取每日不重複地址的用戶數（DAU），可進一步計算週總用戶數或日均用戶數。原始數據僅為每日 DAU，彙總計算在後續步驟處理。

**API Endpoint**：`https://api.sentio.xyz/v1/insights/typus/typus_perp/query`（Metrics endpoint）

---

## 請求 Payload

```json
{
  "version": 9,
  "timeRange": {
    "start": "<UNIX_TIMESTAMP_START>",
    "end": "<UNIX_TIMESTAMP_END>",
    "step": 86400,
    "timezone": "UTC"
  },
  "limit": 20,
  "queries": [
    {
      "eventsQuery": {
        "resource": {
          "name": "",
          "type": "EVENTS"
        },
        "alias": "",
        "id": "a",
        "aggregation": {
          "countUnique": {
            "duration": {
              "value": 1,
              "unit": "day"
            }
          }
        },
        "groupBy": [],
        "limit": 0,
        "functions": [],
        "color": "",
        "disabled": false
      },
      "dataSource": "EVENTS",
      "sourceName": ""
    }
  ],
  "formulas": [],
  "cachePolicy": {
    "noCache": false,
    "cacheTtlSecs": 1036800,
    "cacheRefreshTtlSecs": 43200
  }
}
```

### 時間參數

- 使用 **Unix timestamp (秒)**，同 Query 1 / Query 4
- `step`: `86400`（每日粒度）

---

## 回傳欄位

| 結果 | 欄位路徑 | 類型 | 說明 | 週報指標 |
|------|----------|------|------|---------|
| results[0] | `.matrix.samples[0].metric.displayName` | string | `"<All Events> - DAU"` | — |
| results[0] | `.matrix.samples[0].values[].timestamp` | string (unix) | 該日開始時間 | 日期 |
| results[0] | `.matrix.samples[0].values[].value` | float | 當日不重複用戶數 | Daily Unique Users (DAU) |

---

## 範例回應

```json
{
  "results": [
    {
      "id": "a",
      "alias": "",
      "matrix": {
        "samples": [
          {
            "metric": {
              "displayName": "<All Events> - DAU"
            },
            "values": [
              { "timestamp": "1769990400", "value": 6 },
              { "timestamp": "1770076800", "value": 5 },
              { "timestamp": "1770163200", "value": 9 },
              { "timestamp": "1770249600", "value": 19 },
              { "timestamp": "1770336000", "value": 18 },
              { "timestamp": "1770422400", "value": 7 },
              { "timestamp": "1770508800", "value": 6 },
              { "timestamp": "1770595200", "value": 0 }
            ]
          }
        ]
      }
    }
  ]
}
```

---

## 資料特性

- **回傳量**：8 筆（7 天 + 結束日，結束日通常為 0 因為剛開始）
- **計數方式**：`countUnique` by `distinct_id`（錢包地址），duration=1 day
- **resource name 為空**：代表計算所有事件的不重複用戶，不限特定事件類型
- **數值為整數**（雖然類型是 float）

---

## 在週報中的用途（後續步驟計算）

- **日均用戶數**：7 天 DAU 的平均值（排除結束日的 0）
- **週總不重複用戶**：需另外查詢或從其他數據源取得（DAU 加總 ≠ 週不重複用戶，因為同一用戶可能多天活躍）
- **用戶趨勢**：與上週對比是否成長
