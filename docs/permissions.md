# 權限設計（最小權限原則）

「Prompt 可能被忽略，權限不會」——重要限制用三層機制強制執行：

1. **tools 白名單**（`.claude/agents/*.md` 的 `tools`）：子代理只拿得到列出的工具。
2. **PreToolUse hook**（子代理 frontmatter 的 `hooks`）：每次 Edit / Write 前執行
   `.claude/hooks/guard_paths.py <子代理> <允許路徑...>`，不在允許範圍就 exit 2 擋下，
   並把原因回傳給子代理；擋下紀錄寫入 `.claude/hooks/blocked.log`。
3. **settings.json**：只預先允許 `python -m pytest` / `pytest`，其他 Bash 指令需詢問。

| 角色 | tools | 可編輯路徑（hook） | 執行指令 | 網路 | 設計理由 |
|---|---|---|---|---|---|
| 主 Agent | 全部 | 全部（CLAUDE.md 規定不寫功能程式） | ✔ | ✔ | 指揮與整合 |
| architect | Read, Grep, Glob, Write, Edit | `docs/` | ✘ | ✘ | 只寫規格，不能偷寫程式 |
| coder | Read, Grep, Glob, Write, Edit, Bash | `app/`、`requirements.txt` | 需詢問 | ✘ | 能裝套件試跑，但不能改測試 |
| tester | Read, Grep, Glob, Write, Edit, Bash | `tests/` | pytest 免詢問 | ✘ | 能跑測試，發現 bug 只回報 |
| reviewer | Read, Grep, Glob | 無 | ✘ | ✘ | 沒有編輯權，審查才客觀 |
| db-evaluator | Read, WebSearch, WebFetch | 無 | ✘ | ✔ | 只查資料回報 JSON，可安全並行 |
| security-auditor | Read, Grep, Glob | 無 | ✘ | ✘ | 只負責找問題 |
