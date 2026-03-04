# Query 11: iTLP-TYPUS TVL（iTLP 資金池總鎖定價值）

**用途**：獲取 iTLP-TYPUS 資金池的總 TVL（USD），用於週報的 LP Performance 分析。iTLP-TYPUS 為 100% USDC 組成，無需追蹤幣種組成比例，僅追蹤總 TVL。

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
          "index": "1"
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
      "disabled": true,
      "functions": [],
      "color": ""
    },
    {
      "expression": "sum(a*b)",
      "alias": "Total",
      "id": "B",
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
- `index: "1"` = iTLP-TYPUS 池（mTLP 為 `index: "0"`）
- Formula A（幣種明細）`disabled: true`，不需要組成明細
- Formula B（`sum(a*b)`）`disabled: false`，直接取得總 TVL（USD）

---

## 回傳欄位

回傳結構為 formula B 的 results（因 A disabled，results[0] = formula B）。

| 結果 | 路徑 | 類型 | 說明 |
|------|------|------|------|
| results[0] (formula B) | `.matrix.samples[0].values[].timestamp` | string (unix) | 時間點 |
| results[0] (formula B) | `.matrix.samples[0].values[].value` | float | iTLP-TYPUS 總 TVL（USD） |

---

## 範例回應（節錄）

```json
{
  "results": [
    {
      "id": "B",
      "alias": "Total",
      "matrix": {
        "samples": [
          {
            "metric": {
              "labels": {}
            },
            "values": [
              { "timestamp": "1769990400", "value": 45200.00 },
              { "timestamp": "1770076800", "value": 46800.50 }
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
- **TVL 讀取**：
  ```
  itlp_tvl = results[0].matrix.samples[0].values[-1].value
  ```

---

## 在週報中的用途

- 呈現 iTLP-TYPUS 資金池規模，追蹤 WoW TVL 變化
- 結合 mTLP TVL（Q9）一起呈現平台整體 TLP 資金池規模
- iTLP TVL 成長代表資金流入，適合在 LP Performance 段落提及
