# Typus Perp 事件流程圖

> 描述各 event table 之間的關係、觸發順序、以及跨表關聯鍵。

---

## 交易生命週期

```
PlaceOrder (order_type = 'Limit')           ← 使用者開倉下單（不論限價或市價，order_type 都是 Limit）
    │
    ├── [市價單立即成交]
    │       ↓
    │   OrderFilled (order_type = 'Open')     ← 開倉成交
    │
    ├── [限價單掛單等待]
    │       ↓
    │   CancelOrder                           ← 使用者或系統取消掛單
    │       或
    │   OrderFilled (order_type = 'Open')     ← 觸價成交（由 cranker 執行）
    │
    ↓ [持倉期間]
    │
    ├── PlaceOrder (order_type = 'Limit')     ← 加倉下單
    │       ↓
    │   OrderFilled (order_type = 'Increase') ← 加倉成交
    │
    ├── PlaceOrder (order_type = 'TP')        ← 設定止盈單
    ├── PlaceOrder (order_type = 'SL')        ← 設定止損單
    ├── IncreaseCollateral                    ← 追加保證金
    ├── ReleaseCollateral                     ← 釋放多餘保證金
    ├── RealizeFunding                        ← 資金費率結算（週期性，由 cranker 觸發）
    │
    ↓ [平倉]
    │
    ├── PlaceOrder (order_type = 'TP')        ← 使用者主動關倉（order_type 也是 TP）
    │       ↓
    │   OrderFilled (order_type = 'Close')    ← 平倉成交（含 TP/SL 觸發）
    │       ↓
    │   RemovePosition                        ← 倉位完全關閉後移除
    │
    └── Liquidate                             ← 強制清算（保證金不足，由 cranker 執行）
            ↓
        RemovePosition                        ← 倉位移除
```

### order_type 說明

**PlaceOrder 的 order_type**：

| order_type | 說明 |
|-----------|------|
| `Limit` | 開倉或加倉（不論限價或市價，order_type 都是 Limit） |
| `Market` | 市價單立即成交時（`filled = true`） |
| `TP` | 止盈單（Take Profit），也用於使用者主動關倉 |
| `SL` | 止損單（Stop Loss） |

> 判斷邏輯（processor.ts）：`filled` → Market; `reduce_only && !is_stop_order` → TP; `reduce_only && is_stop_order` → SL; 其他 → Limit

**OrderFilled 的 order_type**：

| order_type | 判斷邏輯（processor.ts） |
|-----------|------------------------|
| `Open` | `linked_position_id == undefined`（新建倉位） |
| `Increase` | `position_size > filled_size`（加倉，倉位已存在） |
| `Close` | 其他情況（平倉或減倉） |

### cranker 機制

- `is_cranker = true`：表示該操作由系統自動執行者（cranker）觸發，而非使用者本人
- 常見場景：限價單觸價執行、TP/SL 觸發、清算、資金費率結算
- 判斷邏輯：`event.sender != event.data_decoded.user`

---

## LP 操作（獨立於交易生命週期）

```
MintLp     ← LP 注入流動性（存入代幣，獲得 TLP token）
RedeemLp   ← LP 發起贖回請求（冷卻期開始）
BurnLp     ← LP 完成提取（冷卻期結束，燒毀 TLP，取回代幣）
Swap       ← LP 池內資產互換（如 SUI → USDC）
```

### 平台放貸操作

```
WithdrawLending  ← 平台方將 LP 資金拿去放貸後，提取借貸收益時觸發（非使用者操作）
```

> WithdrawLending 是平台層級事件，與 LP 使用者無直接關聯。平台會將 LP 池中的資金進行借貸以產生額外收益，提取這些收益時觸發此事件。

---

## 資金費率

```
UpdateFundingRate  ← 系統更新資金費率指數（全局事件，非針對個人）
RealizeFunding     ← 個別倉位結算資金費（基於費率指數差異）
```

---

## 質押（Stake Pool）

```
Stake              ← 質押 LP token
Unstake            ← 解除質押
HarvestIncentive   ← 領取質押獎勵
```

---

## 跨表關聯鍵

| 關聯 | 鍵 | 說明 |
|------|-----|------|
| PlaceOrder → OrderFilled | `base_token` + `order_id` | 下單到成交（order_id 在每個 base_token 內獨立排序，必須先對齊 base_token） |
| PlaceOrder → CancelOrder | `base_token` + `order_id` | 下單到取消 |
| OrderFilled → OrderFilled | `base_token` + `position_id` | 同倉位的 Open 與 Close |
| OrderFilled → Liquidate | `base_token` + `position_id` | 開倉後被清算 |
| OrderFilled → RealizeFunding | `base_token` + `position_id` | 持倉期間的資金費結算 |
| IncreaseCollateral / ReleaseCollateral | `base_token` + `position_id` | 保證金調整 |
| 所有交易事件 | `distinct_id` | 交易者地址（= sender） |
| MintLp / BurnLp | `index` | LP Pool 索引（0 = mTLP, 1 = iTLP） |

---

## 模組對照

| 模組 | 事件 |
|------|------|
| `position` | OrderFilled, RealizeFunding, RemovePosition |
| `trading` | Liquidate, PlaceOrder, CancelOrder, ReleaseCollateral, IncreaseCollateral, UpdateFundingRate |
| `lp_pool` | MintLp, BurnLp, RedeemLp, Swap, WithdrawLending |
| `stake_pool` | Stake, Unstake, HarvestIncentive |

---

*建立於 2026-04-02，基於 processor.ts 事件處理邏輯。*
