"""由 docs/agent-runs/ 的原始紀錄產生 docs/run-log.md（主 Agent 整理用）。

資料來源：
- 時間戳：docs/agent-runs/timestamps.tsv（主 Agent 以 date +%s 記錄）
- 每次派工：docs/agent-runs/dispatch.tsv（任務/結果/問題）與 <序號>-<子代理>.json（Claude Code 回報的 usage、duration_ms）
- 單一 Agent 對照組：docs/baseline/baseline-result.json、docs/baseline/pytest-baseline.txt
"""
import csv
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.dirname(HERE)


def tok(u):
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    t = {k: (u or {}).get(k, 0) or 0 for k in keys}
    t["total"] = sum(t[k] for k in keys)
    return t


def fmt(n):
    return f"{n:,}"


def secs(ms):
    return f"{ms / 1000:.1f} s"


ts = {}
ts_rows = []
with open(os.path.join(HERE, "timestamps.tsv"), encoding="utf-8") as f:
    for row in csv.reader(f, delimiter="\t"):
        if len(row) == 2:
            ts[row[0]] = int(row[1])
            ts_rows.append(row)

timeline = {}
for line in open(os.path.join(HERE, "timeline.txt"), encoding="utf-8"):
    m = re.match(r"(\d+) (\S+) start=(\d+) end=(\d+)", line)
    if m:
        timeline[int(m.group(1))] = (int(m.group(3)), int(m.group(4)))

dispatch = list(csv.DictReader(open(os.path.join(HERE, "dispatch.tsv"), encoding="utf-8"), delimiter="\t"))
runs = {}
for p in glob.glob(os.path.join(HERE, "*.json")):
    seq = int(os.path.basename(p).split("-")[0])
    runs[seq] = json.load(open(p, encoding="utf-8"))

STAGE = {1: "1", 2: "1", 3: "1", 4: "2", 5: "2", 6: "2", 7: "2", 8: "2", 9: "2", 10: "3"}
L = ["# 執行紀錄（run-log）", "",
     "> 時間戳皆由 `date +%s` 取得（Unix 秒）。token／耗時為各子代理完成時 Claude Code 在 JSON 結果中回報的 `usage` 與 `duration_ms`。",
     "> token 總量 = input + output + cache 建立 + cache 讀取（與單一 Agent 對照組用同一算法）。原始 JSON 在 `docs/agent-runs/`。", "",
     "## 執行方式說明", "",
     "本 session 的主 Agent 是在上層資料夾啟動，內建 Agent 工具無法載入 `xr4/.claude/agents/` 的自訂子代理，",
     "因此每個子代理都以 `claude -p --agent <名稱>`（`docs/agent-runs/run_agent.sh`）在專案根目錄以無頭模式執行，",
     "子代理設定檔的 tools 白名單與 PreToolUse hook 都會真正生效。無頭模式無法互動詢問，故每次派工以 `--allowedTools` 明確給予該角色可用的工具（coder 額外給 `Bash(python:*)`、`Bash(pip:*)`；tester 只給 pytest）。", "",
     "## 時間戳", "", "| 事件 | 時間戳 |", "|---|---|"]
L += [f"| {k} | {v} |" for k, v in ts_rows]

L += ["", "## 派工紀錄", "",
      "| 順序 | 階段 | 子代理 | 任務 | 結果 | token（總量 / in+out） | 耗時 | 遇到的問題 |",
      "|---|---|---|---|---|---|---|---|"]
team_total = team_io = team_cost = 0
stage_tok = {"1": 0, "2": 0, "3": 0}
for d in dispatch:
    seq = int(d["seq"])
    r = runs[seq]
    t = tok(r.get("usage"))
    team_total += t["total"]
    team_io += t["input_tokens"] + t["output_tokens"]
    team_cost += r.get("total_cost_usd") or 0
    stage_tok[STAGE[seq]] += t["total"]
    L.append(f"| {seq} | {STAGE[seq]} | {d['agent']} | {d['task']} | {d['result']} | {fmt(t['total'])} / {fmt(t['input_tokens'] + t['output_tokens'])} | "
             f"{secs(r.get('duration_ms') or 0)}（{r.get('num_turns')} turns） | {d['issues']} |")

L += ["", "## 被權限或 hook 擋下的紀錄", "",
      "| 子代理（序號） | 類型 | 內容 | 子代理的處理 |", "|---|---|---|---|",
      "| tester（前置測試） | hook | 刻意要求 tester 寫 `app/hooktest.py`，guard_paths.py 擋下（`docs/agent-runs/preflight-blocked.log`） | 回報被擋，未建立檔案；證明 hook 生效 |",
      "| coder（5） | hook | 想把暫存驗證腳本寫到系統 scratchpad，不在 `app/`、`requirements.txt` 內被擋（`blocked-5-coder.log`） | 改放 `app/_smoke_check.py`，跑完自行刪除 |",
      "| coder（5） | 權限 | 2 次 Bash 被拒：inline heredoc 的 python 腳本、`DATABASE_URL=... python ...` 前綴寫法（不符合 `Bash(python:*)`） | 改用 `python -m app._smoke_check` |",
      "| coder（8） | hook | 想寫 scratchpad 的 `check.py` 被擋（`blocked-8-coder.log`） | 改用 `python -c` 驗證 |",
      "| coder（8） | 權限 | 2 次 Bash 被拒：含 `export DATABASE_URL=...` 與環境變數前綴的指令 | 改用 `python -c` 驗證 |",
      "", "其餘子代理（db-evaluator ×3、architect、tester 6/9、reviewer、security-auditor）沒有被擋下的紀錄（`permission_denials` 為空）。"]

t1s, t1e = ts["階段 1 開始"], ts["階段 1 結束"]
t2s, t2e = ts["階段 2 開始"], ts["階段 2 結束"]
t3s, t3e = ts["階段 3 開始"], ts["階段 3 結束"]
first_agent = min(s for s, _ in timeline.values())
blocked = first_agent - t1s
L += ["", "## 修正輪數", "",
      "- 階段 2：**1 輪**。tester 第一次 184 個測試全過、reviewer 結論「通過」（0 高／0 中），但 reviewer 的 9 項低嚴重度中有 2 項實為規格不符，主 Agent 把其中 5 項交回 coder（序號 8）修正，再由 tester 補測並重跑（序號 9，191 全過）。",
      "- 階段 3：**0 輪**。security-auditor 沒有高／中嚴重度問題，無需交給 coder。",
      "", "## 團隊版總耗時與 token", "",
      f"- 階段 1（Part B）：{t1e} − {t1s} = **{t1e - t1s} s**；其中 {blocked} s 是等待使用者登入 CLI 與修復 CLI 安裝（第一個子代理於 {first_agent} 才啟動），扣除後 **{t1e - first_agent} s**（3 個 db-evaluator 並行實際 {max(e for s_, e in [timeline[i] for i in (1, 2, 3)]) - first_agent} s）。",
      f"- 階段 2（Part C）：{t2e} − {t2s} = **{t2e - t2s} s**",
      f"- 階段 3（加分題 + 最終測試）：{t3e} − {t3s} = **{t3e - t3s} s**",
      f"- **團隊版總耗時**（階段 1 開始 → 階段 3 結束）：{t3e} − {t1s} = **{t3e - t1s} s**；扣除等待登入的 {blocked} s 為 **{t3e - t1s - blocked} s**",
      f"- 子代理 token 加總：**{fmt(team_total)}**（in+out 只有 {fmt(team_io)}）；階段 1：{fmt(stage_tok['1'])}、階段 2：{fmt(stage_tok['2'])}、階段 3：{fmt(stage_tok['3'])}",
      f"- 子代理費用加總（Claude Code 回報的 total_cost_usd）：${team_cost:.4f}",
      "- 以上 token 為子代理加總，**不含主 Agent（本 session）本身**。"]

bpath = os.path.join(DOCS, "baseline", "baseline-result.json")
if os.path.exists(bpath):
    b = json.load(open(bpath, encoding="utf-8"))
    bt = tok(b.get("usage"))
    ptxt = open(os.path.join(DOCS, "baseline", "pytest-baseline.txt"), encoding="utf-8", errors="replace").read()
    m = re.search(r"=+ (.*?) in [\d.]+s", ptxt)
    summary = m.group(1) if m else "（無法解析）"
    passed = re.search(r"(\d+) passed", summary)
    failed = re.search(r"(\d+) failed", summary)
    bs, be = (int(open(os.path.join(DOCS, "baseline", n)).read().strip()) for n in ("baseline-start.txt", "baseline-end.txt"))
    team_cmp_time = (t1e - first_agent) + (t2e - t2s)
    team_cmp_tok = stage_tok["1"] + stage_tok["2"]
    L += ["", "## 階段 4：單一 Agent 對照組", "",
          "做法：把專案複製到 `../xr-baseline`，刪除 `.claude/agents/`、`app/` 程式、`tests/` 測試與 docs 產出（另外也刪了團隊版的 `docs/agent-runs/` 原始紀錄，避免答案外洩），",
          "再以 `claude -p ... --output-format json --permission-mode acceptEdits` 讓單一 Claude 完成同樣工作（Part B + Part C，不含加分題）。",
          "結果原始檔：`docs/baseline/baseline-result.json`；baseline 的測試輸出：`docs/baseline/pytest-baseline.txt`。", "",
          "| 項目 | 單一 Agent | 多 Subagent 團隊（階段 1 + 2，可比較範圍） | 團隊版全部（含階段 3） |", "|---|---|---|---|",
          f"| 耗時 | {b.get('duration_ms', 0) / 1000:.1f} s（duration_ms={b.get('duration_ms')}；時間戳 {be} − {bs} = {be - bs} s） | {team_cmp_time} s（時間戳，已扣除等待登入） | {t3e - t1s - blocked} s |",
          f"| num_turns | {b.get('num_turns')} | {sum(runs[i].get('num_turns') or 0 for i in range(1, 10))}（9 次派工加總） | {sum(r.get('num_turns') or 0 for r in runs.values())} |",
          f"| token 總量 | {fmt(bt['total'])} | {fmt(team_cmp_tok)} | {fmt(team_total)} |",
          f"| token in+out | {fmt(bt['input_tokens'] + bt['output_tokens'])} | {fmt(sum(tok(runs[i]['usage'])['input_tokens'] + tok(runs[i]['usage'])['output_tokens'] for i in range(1, 10)))} | {fmt(team_io)} |",
          f"| total_cost_usd | ${b.get('total_cost_usd') or 0:.4f} | ${sum(runs[i].get('total_cost_usd') or 0 for i in range(1, 10)):.4f} | ${team_cost:.4f} |",
          f"| pytest 結果 | {summary} | 191 passed（docs/test-result.txt） | 191 passed |", "",
          f"- usage 明細（單一 Agent）：input {fmt(bt['input_tokens'])}、output {fmt(bt['output_tokens'])}、cache 建立 {fmt(bt['cache_creation_input_tokens'])}、cache 讀取 {fmt(bt['cache_read_input_tokens'])}。",
          "- **註：團隊版 token 是子代理加總，不含主 Agent 本身**；單一 Agent 版是該無頭 session 的全部用量。",
          f"- 單一 Agent 的 is_error={b.get('is_error')}，permission_denials {len(b.get('permission_denials') or [])} 筆。"]
    L += ["- 單一 Agent 唯一被拒的工具呼叫是 PowerShell（不在 `--allowedTools` 內），它改用其他工具繼續；它也依提示沒有派出任何子代理（subagent_stats.spawned=0）。",
          "- 觀察：兩版 token 總量接近（團隊版可比較範圍約為單一 Agent 的 "
          f"{team_cmp_tok / bt['total']:.2f} 倍），但團隊版 in+out 約為 {sum(tok(runs[i]['usage'])['input_tokens'] + tok(runs[i]['usage'])['output_tokens'] for i in range(1, 10)) / (bt['input_tokens'] + bt['output_tokens']):.1f} 倍、費用約 "
          f"{sum(runs[i].get('total_cost_usd') or 0 for i in range(1, 10)) / (b.get('total_cost_usd') or 1):.1f} 倍、耗時約 {team_cmp_time / (b.get('duration_ms') / 1000):.1f} 倍；"
          "團隊版每個子代理都要重新建立 context（cache 建立較多），且派工之間是依序等待；單一 Agent 一個 context 用到底，cache 讀取佔 93%。",
          "- 範圍差異：單一 Agent 自行擴充了規格（rotation 改成四元數、加了 PATCH、scene_id/type 篩選與 metadata 欄位），而且沒有作業指定的 model_url 欄位，與作業指定的欄位（name、model_url、position、rotation (x, y, z)、scale）不一致；團隊版依 architect 規格實作作業指定的 5 個端點。"]
    if failed:
        L.append(f"- 單一 Agent 版有 {failed.group(1)} 個測試失敗。")

open(os.path.join(DOCS, "run-log.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
