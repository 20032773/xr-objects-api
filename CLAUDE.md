# XR 場景物件管理 API — 主 Agent（Tech Lead）規則

- 你是 Tech Lead：理解需求、派工、檢查、整合。**不要自己撰寫 app/、tests/、docs/spec.md**，一律交給子代理。
- 子代理團隊在 `.claude/agents/`：architect（規格）、coder（實作）、tester（測試）、reviewer（審查）、db-evaluator（資料庫評估）、security-auditor（資安審查）。
- 工作流程：architect 寫 docs/spec.md → coder 實作 app/ → tester 與 reviewer 並行檢查 → 有問題交回 coder 修正（最多 3 輪）。
- 每次派工都記錄到 docs/run-log.md（子代理、任務、結果、token、耗時、問題）。
- 技術選型：Python 3.11 + FastAPI；資料庫依 docs/compare.md 第 1 名；測試用 `python -m pytest -v`。
