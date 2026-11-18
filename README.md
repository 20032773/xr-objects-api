# XR 場景物件管理 API（Subagent 團隊開發）

以 Claude Code 子代理團隊（architect / coder / tester / reviewer / db-evaluator / security-auditor）開發的 FastAPI + SQLite CRUD API。

- `.claude/agents/`：子代理設定（tools 白名單 + PreToolUse hook）
- `.claude/hooks/guard_paths.py`：限制子代理可編輯的路徑
- `docs/compare.md`（Part B）、`docs/spec.md`（規格）、`docs/permissions.md`（權限設計）、`docs/security.md`（OWASP 審查）
- `docs/run-log.md`：派工、token、耗時紀錄；`docs/agent-runs/`：每次派工的原始 JSON
- `app/`：API 程式；`tests/`：pytest 測試

```bash
pip install -r requirements.txt
uvicorn app.main:app
python -m pytest -v
```
