# Query 4: Daily Volume by Token & Side（每日幣種方向交易量）

**用途**：獲取過去一週中每天各幣種、各方向（Long / Short / Liquidate）的交易量（USD），用於分析交易者偏好與市場情緒。

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
      "metricsQuery": {
        "query": "trading_volume_usd",
        "alias": "{{base_token}}, {{side}}",
        "id": "a",
        "labelSelector": {},
        "aggregate": {
          "op": "SUM",
          "grouping": [
            "base_token",
            "side"
          ]
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
    "cacheTtlSecs": 1036800,
    "cacheRefreshTtlSecs": 43200
  }
}
```

### 時間參數

- 使用 **Unix timestamp (秒)**，同 Query 1
- `step`: `86400`（每日粒度，1 天 = 86400 秒）
- 範例：2026-02-02 ~ 2026-02-09 → start=`1769990400`, end=`1770595200`

### 關鍵設計

- **`aggregate.grouping`**: `["base_token", "side"]` — 按幣種 × 方向分組
- **`rollup_delta`**: 計算每日增量（而非累積值），duration=1d
- **`alias`**: `"{{base_token}}, {{side}}"` — 動態顯示名稱

---

## 回傳結構

回傳多組時間序列，每組代表一個 `base_token + side` 組合：

```json
{
  "results": [
    {
      "id": "a",
      "alias": "{{base_token}}, {{side}}",
      "matrix": {
        "samples": [
          {
            "metric": {
              "labels": {
                "base_token": "SUI",
                "side": "Long"
              }
            },
            "values": [
              { "timestamp": "1769990400", "value": 0.0 },
              { "timestamp": "1770076800", "value": 340.79 },
              { "timestamp": "1770163200", "value": 24480.37 }
            ]
          },
          {
            "metric": {
              "labels": {
                "base_token": "SUI",
                "side": "Short"
              }
            },
            "values": [...]
          },
          {
            "metric": {
              "labels": {
                "base_token": "TYPUS",
                "side": "Long"
              }
            },
            "values": [...]
          }
        ]
      }
    }
  ]
}
```

---

## 回傳欄位

| 欄位路徑 | 類型 | 說明 |
|----------|------|------|
| `samples[].metric.labels.base_token` | string | 幣種（SUI, BTC, ETH, TYPUS, SOL, XAU, JPY, HYPE, WAL 等） |
| `samples[].metric.labels.side` | string | 方向：`Long` / `Short` / `Liquidate` |
| `samples[].values[].timestamp` | string (unix) | 該日開始時間 |
| `samples[].values[].value` | float | 該日該幣種該方向的交易量 (USD) |

---

## 實際觀察到的幣種與方向（2026-02-02 ~ 02-09）

| 幣種 | Long | Short | Liquidate |
|------|------|-------|-----------|
| SUI | ✅ 主要交易對 | ✅ 主要交易對 | ✅ |
| TYPUS | ✅ | ✅ | ✅ |
| BTC | ✅ | ✅ | ✅ |
| ETH | — (少量) | ✅ | — |
| SOL | ✅ | ✅ | — |
| XAU | ✅ | ✅ | — |
| JPY | ✅ | — | — |
| HYPE | ✅ | — | — |
| WAL | — | ✅ | — |

> 幣種清單會隨時間變化，不是固定的。資料處理時應動態解析所有出現的 base_token。

---

## 在週報中的用途

- 分析哪些幣種是當週**交易量最大**的交易對
- 分析市場情緒：Long vs Short 比例
- 清算事件追蹤（Liquidate 金額）
- 可彙總為「本週熱門交易對排行」表格

### 建議的週報呈現方式

1. **按幣種彙總週交易量**（Long + Short + Liquidate），排序取 Top N
2. **Long/Short 比例**分析（偏多/偏空）
3. **清算金額**摘要
