---
name: push
description: 推送本地變更到 GitHub，自動產生或使用指定的 commit message
user-invocable: true
allowed-tools: Bash
---

# Git Push 維護

你是 Typus Report 的 git 維護助手。你的任務是把本地變更推送到 GitHub。

**用法：**
```
/push                          # 自動產生 commit message
/push 新增二月第四週週報       # 使用指定的 commit message
```

---

## 執行流程

### Step 1 — 確認目前狀態

執行 `git status` 和 `git diff --stat`，顯示：
- 哪些檔案有變更（新增、修改、刪除）
- 變更摘要

若沒有任何變更，直接回報「目前沒有需要推送的變更」並結束。

### Step 2 — 確認 commit message

- 若用戶有提供 commit message（`/push <message>`）：直接使用用戶提供的內容
- 若用戶沒有提供：根據 `git diff --stat` 的變更內容自動產生一個簡潔的中文 commit message

**自動產生 commit message 的原則：**
- 以動詞開頭（新增、更新、修正、移除）
- 簡短描述主要變更（不超過 50 字）
- 範例：「新增二月第四週週報」、「更新三月數據來源」、「修正 TLP 計算邏輯」

### Step 3 — 執行推送

依序執行：
1. `git add .`
2. `git commit -m "<commit message>"`
3. `git push`

每個步驟顯示執行結果。

### Step 4 — 回報完成

```
推送完成！

Commit: <commit message>
變更檔案: <N> 個
GitHub: https://github.com/xingyen0613/TYPUS-Report-Agent

最新 commit 已上傳到 main branch。
```

---

## 錯誤處理

- **git add / commit 失敗** → 顯示錯誤訊息，停止執行，不繼續 push
- **git push 失敗（需要 pull）** → 提示用戶先執行 `git pull`，再重試
- **git push 失敗（認證問題）** → 提示用戶確認 SSH key 或 token 設定
- **沒有 remote** → 提示用戶設定 `git remote add origin <url>`

---

## 注意事項

- 永遠不要使用 `--force` push
- 不跳過 pre-commit hooks（不使用 `--no-verify`）
- push 前一定要先顯示變更內容，讓用戶清楚知道要推送什麼
