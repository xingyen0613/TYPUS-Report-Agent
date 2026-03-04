---
name: git
description: 統一 git 操作：/git commit 記錄當前變更到暫存，/git push 合併所有紀錄並推送
user-invocable: true
allowed-tools: Bash, Read, Write, Edit
---

# Git 維護助手

你是 Typus Report 的 git 維護助手，負責管理跨 session 的 git 操作。

**用法：**
```
/git commit                    # 分析當前變更並記錄到 pending-commits
/git push                      # 合併所有 pending 紀錄 + 當前變更，推送到 GitHub
/git push 新增二月第四週週報   # 使用指定的 commit message 推送
```

**pending-commits 路徑：** `.claude/skills/git/pending-commits.md`

---

## `/git commit` 流程

### Step 1 — 確認目前狀態

執行以下指令並顯示結果：
```bash
git status
git diff --stat
```

若沒有任何未暫存或已暫存的變更，回報：「目前沒有未記錄的變更」並結束。

### Step 2 — 分析並產生描述

根據 `git diff --stat` 的變更內容自動分析，產生 1-2 句中文描述：
- 以動詞開頭（新增、更新、修正、移除、整理）
- 不超過 50 字
- 描述主要變更的本質，不只列出檔案名稱
- 範例：「新增三月第一週週報草稿與定稿」、「更新 Sentio 數據查詢新增 Q11 iTLP TVL」

### Step 3 — 附加到 pending-commits

將描述附加到 `.claude/skills/git/pending-commits.md`，格式：
```
- [HH:MM] <描述>
```

若檔案不存在，先建立（內容只有這一行）。

### Step 4 — 顯示目前所有 pending-commits

讀取並顯示 `.claude/skills/git/pending-commits.md` 的完整內容，讓用戶確認所有待推送的紀錄。

---

## `/git push` 流程

### Step 1 — 確認目前狀態

執行並顯示：
```bash
git status
git diff --stat
```

### Step 2 — 讀取 pending-commits

若 `.claude/skills/git/pending-commits.md` 存在，讀取並顯示內容。

### Step 3 — 確認是否有變更

若 git status 顯示沒有任何變更（clean working tree，無任何 staged/unstaged 變更），回報「目前沒有需要推送的變更」並結束。

### Step 4 — 確認 commit message

**若用戶有提供 commit message**（`/git push <message>`）：直接使用用戶提供的內容。

**若用戶沒有提供**：同時參考以下兩個來源產生完整描述：
1. `.claude/skills/git/pending-commits.md` 的所有紀錄（若存在）
2. 當前 `git diff --stat` 的變更

合併成一個簡潔的中文 commit message：
- 以動詞開頭
- 不超過 50 字
- 若 pending-commits 有多條紀錄，選最重要的或合併成一句
- 範例：「新增週報並更新數據來源配置」

**自動產生原則：**
- 以動詞開頭（新增、更新、修正、移除、整理）
- 簡短描述主要變更（不超過 50 字）

### Step 5 — 執行推送

依序執行：
1. `git add .`
2. `git commit -m "<commit message>"`
3. `git push`

每個步驟顯示執行結果。

### Step 6 — Push 成功後

Push 成功後：
1. 刪除 `.claude/skills/git/pending-commits.md`
2. 回報完成：

```
推送完成！

Commit: <commit message>
變更檔案: <N> 個
GitHub: https://github.com/xingyen0613/TYPUS-Report-Agent

最新 commit 已上傳到 main branch。
```

---

## 錯誤處理

- **git add / commit 失敗** → 顯示錯誤訊息，停止執行，不繼續 push，**不清除 pending-commits**
- **git push 失敗（需要 pull）** → 提示用戶先執行 `git pull`，再重試，**不清除 pending-commits**
- **git push 失敗（認證問題）** → 提示用戶確認 SSH key 或 token 設定，**不清除 pending-commits**
- **沒有 remote** → 提示用戶設定 `git remote add origin <url>`，**不清除 pending-commits**

> pending-commits 只在 push **成功後**才清除，確保失敗重試時紀錄不丟失。

---

## 注意事項

- 永遠不要使用 `--force` push
- 不跳過 pre-commit hooks（不使用 `--no-verify`）
- push 前一定要顯示變更內容，讓用戶清楚知道要推送什麼
