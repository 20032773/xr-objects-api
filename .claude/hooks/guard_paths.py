#!/usr/bin/env python
"""PreToolUse hook：限制子代理可編輯的路徑。

用法（寫在子代理 frontmatter 的 hooks 裡）：
    python .claude/hooks/guard_paths.py <子代理名稱> <允許路徑1> [<允許路徑2> ...]

允許路徑以 "/" 結尾代表資料夾（含子資料夾），否則代表單一檔案；皆相對於專案根目錄。
不在允許範圍內就 exit 2，Claude Code 會擋下該次 Edit/Write，並把 stderr 的原因回傳給子代理。
每次擋下都會記錄到 .claude/hooks/blocked.log，方便主 Agent 統計。
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = Path(__file__).resolve().parent / "blocked.log"


def block(agent: str, target: str, allowed: list[str]) -> None:
    msg = (
        f"[guard_paths] 已擋下 {agent} 對 {target} 的編輯。"
        f" {agent} 只能編輯：{', '.join(allowed) or '（無）'}。"
        " 若需要修改其他檔案，請在回報中說明，交由主 Agent 派給負責的子代理。"
    )
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{int(time.time())}\t{agent}\t{target}\n")
    except OSError:
        pass
    print(msg, file=sys.stderr)
    sys.exit(2)


def main() -> int:
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print("[guard_paths] 缺少子代理名稱參數", file=sys.stderr)
        return 2
    agent, allowed = sys.argv[1], sys.argv[2:]
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except Exception:
        block(agent, "（無法解析的 hook 輸入）", allowed)
        return 2
    tool_input = data.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")
    if not target:
        return 0

    p = Path(target)
    if not p.is_absolute():
        p = Path(data.get("cwd") or ROOT) / p
    try:
        rel = p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        block(agent, target, allowed)
        return 2

    for a in allowed:
        if (a.endswith("/") and rel.startswith(a)) or rel == a:
            return 0
    block(agent, rel, allowed)
    return 2


if __name__ == "__main__":
    sys.exit(main())
