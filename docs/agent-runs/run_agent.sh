#!/usr/bin/env bash
# 用法：run_agent.sh <序號> <子代理> <任務提示> [額外 claude 參數...]
# 以無頭模式執行 .claude/agents/<子代理>.md，輸出 JSON（含 duration_ms、usage、total_cost_usd）到 docs/agent-runs/
set -u
cd "$(dirname "$0")/../.."
seq="$1"; agent="$2"; prompt="$3"; shift 3
out="docs/agent-runs/${seq}-${agent}.json"
start=$(date +%s)
claude -p --agent "$agent" "$prompt" --output-format json --permission-mode acceptEdits "$@" < /dev/null > "$out" 2> "docs/agent-runs/${seq}-${agent}.stderr.txt"
code=$?
end=$(date +%s)
echo "$seq $agent start=$start end=$end exit=$code" >> docs/agent-runs/timeline.txt
echo "$out exit=$code"
