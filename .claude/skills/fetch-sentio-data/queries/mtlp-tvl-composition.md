# Query 9: mTLP TVL Composition（mTLP 資產組成）

**用途**：獲取 mTLP 池中各幣種（SUI、USDC 等）的 USD 價值佔比，用於週報分析 Basket 效應時正確加權 SUI 的影響。

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
        "query": "tvl",
        "alias": "",
        "id": "a",
        "labelSelector": {
          "index": "0"
        },
        "aggregate": {
          "op": "SUM",
          "grouping": [
            "coin_symbol"
          ]
        },
        "functions": [],
        "color": "",
        "disabled": true
      },
      "dataSource": "METRICS",
      "sourceName": ""
    },
    {
      "priceQuery": {
        "id": "b",
        "alias": "",
        "coinId": [],
        "color": "",
        "disabled": true
      },
      "dataSource": "PRICE",
      "sourceName": ""
    }
  ],
  "formulas": [
    {
      "expression": "a*b",
      "alias": "{{coin_symbol}}",
      "id": "A",
      "disabled": false,
      "functions": [],
      "color": ""
    }
  ],
  "cachePolicy": {
    "noCache": false,
    "cacheTtlSecs": 1036800,
    "cacheRefreshTtlSecs": 43200
  }
}
```

**注意**：
- Query `a`（tvl）和 `b`（price）的 `disabled: true` 表示它們不直接回傳數據，僅作為 formula 的輸入
- `index: 0` = mTLP 池
- `aggregate.grouping: ["coin_symbol"]` 會按幣種分組
- Formula `a*b` 將各幣種的 TVL（token 數量）乘以價格，得到 USD 價值
- Formula alias `{{coin_symbol}}` 會被替換為實際幣種名稱（如 SUI、USDC）

---

## 回傳欄位

回傳結構為 formula results，每個 coin_symbol 是一個獨立的 time series sample。

| 結果 | 路徑 | 類型 | 說明 |
|------|------|------|------|
| results[0] (formula A) | `.matrix.samples[N].metric.labels.coin_symbol` | string | 幣種名稱（SUI, USDC 等） |
| results[0] (formula A) | `.matrix.samples[N].values[].timestamp` | string (unix) | 時間點 |
| results[0] (formula A) | `.matrix.samples[N].values[].value` | float | 該幣種在 mTLP 中的 USD 價值 |

---

## 範例回應（節錄）

```json
{
  "results": [
    {
      "id": "A",
      "alias": "{{coin_symbol}}",
      "matrix": {
        "samples": [
          {
            "metric": {
              "labels": {
                "coin_symbol": "SUI"
              }
            },
            "values": [
              { "timestamp": "1769990400", "value": 35000.50 },
              { "timestamp": "1770076800", "value": 33200.10 }
            ]
          },
          {
            "metric": {
              "labels": {
                "coin_symbol": "USDC"
              }
            },
            "values": [
              { "timestamp": "1769990400", "value": 28000.00 },
              { "timestamp": "1770076800", "value": 28500.00 }
            ]
          }
        ]
      }
    }
  ]
}
```

---

## 資料處理

- **時間粒度**：每日（step=86400）
- **取值方式**：取週末（最後一個數據點）的值作為週報快照
- **計算 SUI 權重**：
  ```
  SUI_weight = SUI_USD_value / (SUI_USD_value + USDC_USD_value) * 100
  USDC_weight = USDC_USD_value / (SUI_USD_value + USDC_USD_value) * 100
  ```

---

## 在週報中的用途

- 計算 mTLP 中 SUI 的權重佔比，用於精確分析 Basket 效應
- 例如：SUI 佔 55%，SUI 跌 -12%，Basket 效應 ≈ -6.6%（而非直接用 -12%）
- 此比例會隨市場變動，每週需重新獲取
