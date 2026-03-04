# Query 3: Cumulative Volume（累積交易量）

**用途**：獲取 Typus Protocol 截至目前的累積總交易量（USD）。只需取最新一筆數據。

**API Endpoint**：`https://api.sentio.xyz/v1/insights/typus/typus_perp/query`（Metrics endpoint）

---

## 請求 Payload

```json
{
  "version": 9,
  "timeRange": {
    "start": "<unix_end - 3600>",
    "end": "<unix_end>",
    "step": 3600,
    "timezone": "UTC"
  },
  "limit": 20,
  "queries": [
    {
      "metricsQuery": {
        "query": "trading_volume_usd",
        "alias": "Trading+liq",
        "id": "a",
        "labelSelector": {},
        "aggregate": { "op": "SUM", "grouping": [] },
        "functions": [],
        "color": "",
        "disabled": true
      },
      "dataSource": "METRICS",
      "sourceName": ""
    },
    {
      "eventsQuery": {
        "resource": { "name": "MintLp", "type": "EVENTS" },
        "alias": "MintLp",
        "id": "b",
        "aggregation": {
          "aggregateProperties": { "type": "CUMULATIVE_SUM", "propertyName": "deposit_amount_usd" }
        },
        "groupBy": [], "limit": 0, "functions": [], "color": "", "disabled": true
      },
      "dataSource": "EVENTS",
      "sourceName": ""
    },
    {
      "eventsQuery": {
        "resource": { "name": "BurnLp", "type": "EVENTS" },
        "alias": "BurnLp",
        "id": "c",
        "aggregation": {
          "aggregateProperties": { "type": "CUMULATIVE_SUM", "propertyName": "burn_amount_usd" }
        },
        "groupBy": [], "limit": 0, "functions": [], "color": "", "disabled": true
      },
      "dataSource": "EVENTS",
      "sourceName": ""
    },
    {
      "eventsQuery": {
        "resource": { "name": "Swap", "type": "EVENTS" },
        "alias": "Swap",
        "id": "d",
        "aggregation": {
          "aggregateProperties": { "type": "CUMULATIVE_SUM", "propertyName": "from_amount" }
        },
        "selectorExpr": {
          "logicExpr": {
            "operator": "AND",
            "expressions": [{ "selector": { "key": "from_token", "operator": "EQ", "value": [{ "stringValue": "SUI" }] } }]
          }
        },
        "groupBy": [], "limit": 0, "functions": [], "color": "", "disabled": true
      },
      "dataSource": "EVENTS",
      "sourceName": ""
    },
    {
      "eventsQuery": {
        "resource": { "name": "Swap", "type": "EVENTS" },
        "alias": "Swap",
        "id": "e",
        "aggregation": {
          "aggregateProperties": { "type": "CUMULATIVE_SUM", "propertyName": "from_amount" }
        },
        "selectorExpr": {
          "logicExpr": {
            "operator": "AND",
            "expressions": [{ "selector": { "key": "from_token", "operator": "EQ", "value": [{ "stringValue": "DEEP" }] } }]
          }
        },
        "groupBy": [], "limit": 0, "functions": [], "color": "", "disabled": true
      },
      "dataSource": "EVENTS",
      "sourceName": ""
    },
    {
      "eventsQuery": {
        "resource": { "name": "Swap", "type": "EVENTS" },
        "alias": "Swap",
        "id": "f",
        "aggregation": {
          "aggregateProperties": { "type": "CUMULATIVE_SUM", "propertyName": "from_amount" }
        },
        "selectorExpr": {
          "logicExpr": {
            "operator": "AND",
            "expressions": [{ "selector": { "key": "from_token", "operator": "EQ", "value": [{ "stringValue": "LBTC" }] } }]
          }
        },
        "groupBy": [], "limit": 0, "functions": [], "color": "", "disabled": true
      },
      "dataSource": "EVENTS",
      "sourceName": ""
    },
    {
      "eventsQuery": {
        "resource": { "name": "Swap", "type": "EVENTS" },
        "alias": "Swap",
        "id": "g",
        "aggregation": {
          "aggregateProperties": { "type": "CUMULATIVE_SUM", "propertyName": "from_amount" }
        },
        "selectorExpr": {
          "logicExpr": {
            "operator": "AND",
            "expressions": [{ "selector": { "key": "from_token", "operator": "EQ", "value": [{ "stringValue": "USDC" }] } }]
          }
        },
        "groupBy": [], "limit": 0, "functions": [], "color": "", "disabled": true
      },
      "dataSource": "EVENTS",
      "sourceName": ""
    },
    {
      "priceQuery": { "id": "h", "alias": "", "coinId": [{ "symbol": "SUI" }], "color": "", "disabled": true },
      "dataSource": "PRICE", "sourceName": ""
    },
    {
      "priceQuery": { "id": "i", "alias": "", "coinId": [{ "symbol": "DEEP" }], "color": "", "disabled": true },
      "dataSource": "PRICE", "sourceName": ""
    },
    {
      "priceQuery": { "id": "j", "alias": "", "coinId": [{ "symbol": "LBTC" }], "color": "", "disabled": true },
      "dataSource": "PRICE", "sourceName": ""
    },
    {
      "priceQuery": { "id": "k", "alias": "", "coinId": [{ "symbol": "USDC" }], "color": "", "disabled": true },
      "dataSource": "PRICE", "sourceName": ""
    }
  ],
  "formulas": [
    {
      "expression": "sum(d*h+e*i+f*j+g*k)+c+b+a",
      "alias": "Vol",
      "id": "A",
      "disabled": false,
      "functions": [],
      "color": ""
    }
  ],
  "cachePolicy": {
    "noCache": false,
    "cacheTtlSecs": 43200,
    "cacheRefreshTtlSecs": 1800
  }
}
```

### 時間範圍說明

使用 `"start": unix_end - 3600, "end": unix_end`（Unix timestamp 整數），取目標週週日最後一小時（23:00 ~ 00:00 UTC）的快照。這樣可確保累積量反映該週週末結算值，而非執行當下的即時值。

---

## 回傳欄位

只回傳 formula 結果（所有子 query 均為 `disabled: true`）：

| 結果 | alias | 欄位路徑 | 類型 | 說明 | 週報指標 |
|------|-------|----------|------|------|---------|
| results[0] | Vol | `.matrix.samples[0].values[-1].value` | float | 累積總交易量 | Cumulative Volume (USD) |

> 取 `values` 陣列的**最後一筆**即為最新的累積交易量。

---

## 範例回應（節錄）

```json
{
  "results": [
    {
      "id": "A",
      "alias": "Vol",
      "matrix": {
        "samples": [
          {
            "values": [
              { "timestamp": "1770667200", "value": 66064.61 },
              { "timestamp": "1770670800", "value": 244392.89 }
            ]
          }
        ]
      }
    }
  ]
}
```

---

## 公式邏輯

```
Vol = sum(d*h + e*i + f*j + g*k) + c + b + a
```

| 變數 | 來源 | 說明 |
|------|------|------|
| `a` | trading_volume_usd (METRICS) | 交易 + 清算的累積交易量 (USD) |
| `b` | MintLp deposit_amount_usd (EVENTS) | 累積 LP 鑄造金額 (USD) |
| `c` | BurnLp burn_amount_usd (EVENTS) | 累積 LP 銷毀金額 (USD) |
| `d` | Swap from_amount where from_token=SUI | 累積 SUI Swap 數量（原生單位） |
| `e` | Swap from_amount where from_token=DEEP | 累積 DEEP Swap 數量 |
| `f` | Swap from_amount where from_token=LBTC | 累積 LBTC Swap 數量 |
| `g` | Swap from_amount where from_token=USDC | 累積 USDC Swap 數量 |
| `h` | SUI price (USD) | SUI 即時價格 |
| `i` | DEEP price (USD) | DEEP 即時價格 |
| `j` | LBTC price (USD) | LBTC 即時價格 |
| `k` | USDC price (USD) | USDC 即時價格 |

> Swap 的交易量以原生代幣數量 × 即時幣價換算為 USD，再加上其他已為 USD 的來源。

---

## 資料特性

- **回傳量**：1-2 筆（因為只取一小時的窗口）
- **取值方式**：取最後一筆的 `value` 即為週末累積交易量快照
- **動態時間範圍**：使用 `unix_end - 3600` 到 `unix_end`（Unix timestamp 整數），指向目標週週日 23:00 ~ 00:00 UTC
- **單位**：USD
