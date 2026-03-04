# Query 1: TLP Price（TLP 價格走勢）

**用途**：獲取 Typus Protocol 兩個 TLP（mTLP 和 iTLP-TYPUS）的 USD 價格走勢，用於週報呈現 TLP 價格表現。

---

## 請求 Payload

```json
{
  "version": 9,
  "timeRange": {
    "start": "<UNIX_TIMESTAMP_START>",
    "end": "<UNIX_TIMESTAMP_END>",
    "step": 3600,
    "timezone": "UTC"
  },
  "limit": 20,
  "queries": [
    {
      "metricsQuery": {
        "query": "tlp_price",
        "alias": "mTLP",
        "id": "a",
        "labelSelector": {
          "index": "0"
        },
        "aggregate": null,
        "functions": [],
        "color": "",
        "disabled": false
      },
      "dataSource": "METRICS",
      "sourceName": ""
    },
    {
      "metricsQuery": {
        "query": "tlp_price",
        "alias": "iTLP-TYPUS",
        "id": "b",
        "labelSelector": {
          "index": "1"
        },
        "aggregate": null,
        "functions": [],
        "color": "classic.7",
        "disabled": false
      },
      "dataSource": "METRICS",
      "sourceName": ""
    }
  ],
  "formulas": [],
  "cachePolicy": {
    "noCache": false,
    "cacheTtlSecs": 43200,
    "cacheRefreshTtlSecs": 1800
  }
}
```

**注意**：原始 query 中有一個 SUI priceQuery (id: c, `disabled: true`)，已移除不納入執行。

---

## 回傳欄位

| 結果 | alias | 欄位路徑 | 類型 | 說明 | 週報指標 |
|------|-------|----------|------|------|---------|
| results[0] | mTLP | `.matrix.samples[0].values[].timestamp` | string (unix) | 時間點 | — |
| results[0] | mTLP | `.matrix.samples[0].values[].value` | float | mTLP 價格 | mTLP Price (USD) |
| results[1] | iTLP-TYPUS | `.matrix.samples[0].values[].timestamp` | string (unix) | 時間點 | — |
| results[1] | iTLP-TYPUS | `.matrix.samples[0].values[].value` | float | iTLP-TYPUS 價格 | iTLP-TYPUS Price (USD) |

**Labels**：
- mTLP: `{ "chain": "sui_mainnet", "index": "0" }`
- iTLP-TYPUS: `{ "chain": "sui_mainnet", "index": "1" }`

---

## 範例回應（節錄）

```json
{
  "results": [
    {
      "id": "a",
      "alias": "mTLP",
      "dataSource": "METRICS",
      "matrix": {
        "samples": [
          {
            "metric": {
              "displayName": "tlp_price",
              "labels": {
                "chain": "sui_mainnet",
                "contract_address": "",
                "contract_name": "object",
                "index": "0"
              }
            },
            "values": [
              { "timestamp": "1769990400", "value": 0.895816 },
              { "timestamp": "1769994000", "value": 0.898407 },
              { "timestamp": "1769997600", "value": 0.898407 }
            ]
          }
        ]
      }
    },
    {
      "id": "b",
      "alias": "iTLP-TYPUS",
      "dataSource": "METRICS",
      "matrix": {
        "samples": [
          {
            "metric": {
              "displayName": "tlp_price",
              "labels": {
                "chain": "sui_mainnet",
                "contract_address": "",
                "contract_name": "object",
                "index": "1"
              }
            },
            "values": [
              { "timestamp": "1769990400", "value": 1.000458 },
              { "timestamp": "1769994000", "value": 1.000404 },
              { "timestamp": "1769997600", "value": 1.000109 }
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

- **粒度**：1 小時
- **7 天數據量**：~169 筆/每個 TLP
- **mTLP**：價格通常在 0.8~1.0 USD 波動，受市場影響較大
- **iTLP-TYPUS**：價格極為穩定，約 1.0 USD，波動極小
- **重複值**：部分連續小時的 value 相同，屬正常現象（該時段無鏈上事件更新）

---

## 在週報中的用途

- 呈現 mTLP 和 iTLP-TYPUS 的週度價格走勢
- 計算週開盤價 → 週收盤價的漲跌幅
- 製作每日開收盤摘要表
