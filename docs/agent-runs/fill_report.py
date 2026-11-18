"""填寫 Word 報告：把黃色螢光的【】換成實際內容（資料只取自 docs/ 與 baseline 結果）。

用法：python docs/agent-runs/fill_report.py <github_url>
輸出：XR作業_資工四甲_41218106_鐘仁澤_完成.docx（不進 repo）
"""
import copy
import csv
import glob
import json
import os
import re
import sys

import docx
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")
RUNS = os.path.join(DOCS, "agent-runs")
SRC = os.path.join(ROOT, "XR作業_資工四甲_41218106_鐘仁澤.docx")
DST = os.path.join(ROOT, "XR作業_資工四甲_41218106_鐘仁澤_完成.docx")
GITHUB = sys.argv[1]
TODAY = sys.argv[2] if len(sys.argv) > 2 else "2026/11/18"


def tok(u):
    return sum((u or {}).get(k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def n(x):
    return f"{x:,}"


# ---------- 讀取資料 ----------
runs = {int(os.path.basename(p).split("-")[0]): json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(RUNS, "*.json"))}
ts = dict((k, int(v)) for k, v in csv.reader(open(os.path.join(RUNS, "timestamps.tsv"), encoding="utf-8"), delimiter="\t"))
timeline = {}
for line in open(os.path.join(RUNS, "timeline.txt"), encoding="utf-8"):
    m = re.match(r"(\d+) (\S+) start=(\d+) end=(\d+)", line)
    if m:
        timeline[int(m.group(1))] = (int(m.group(3)), int(m.group(4)))
first_agent = min(s for s, _ in timeline.values())
blocked = first_agent - ts["階段 1 開始"]
partB_time = ts["階段 1 結束"] - first_agent
partB_par = max(timeline[i][1] for i in (1, 2, 3)) - first_agent
partC_time = ts["階段 2 結束"] - ts["階段 2 開始"]
tokB = sum(tok(runs[i]["usage"]) for i in (1, 2, 3))
tokC = sum(tok(runs[i]["usage"]) for i in range(4, 10))
tok3 = tok(runs[10]["usage"])

evals = [json.loads(runs[i]["result"]) for i in (1, 2, 3)]
evals.sort(key=lambda r: (r["total"], r["scores"]["testing"], r["scores"]["python"]), reverse=True)

compare_md = open(os.path.join(DOCS, "compare.md"), encoding="utf-8").read()
choice = compare_md.split("## 選擇與理由", 1)[1].strip().split("\n")[0].replace("**", "")

tr = open(os.path.join(DOCS, "test-result.txt"), encoding="utf-8", errors="replace").read()
t_pass = int(re.search(r"(\d+) passed", tr).group(1))
t_fail = int(m.group(1)) if (m := re.search(r"(\d+) failed", tr)) else 0
t_total = t_pass + t_fail

b = json.load(open(os.path.join(DOCS, "baseline", "baseline-result.json"), encoding="utf-8"))
btok = tok(b.get("usage"))
bdur = (b.get("duration_ms") or 0) / 1000
bpy = open(os.path.join(DOCS, "baseline", "pytest-baseline.txt"), encoding="utf-8", errors="replace").read()
b_pass = int(m.group(1)) if (m := re.search(r"(\d+) passed", bpy)) else 0
b_fail = int(m.group(1)) if (m := re.search(r"(\d+) failed", bpy)) else 0
team_cmp_tok = tokB + tokC
team_cmp_time = partB_time + partC_time
ratio_tok = team_cmp_tok / btok if btok else 0
ratio_time = team_cmp_time / bdur if bdur else 0
_io = lambda u: (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
io_ratio = sum(_io(runs[i]["usage"]) for i in range(1, 10)) / _io(b["usage"])
cost_ratio = sum(runs[i].get("total_cost_usd") or 0 for i in range(1, 10)) / (b.get("total_cost_usd") or 1)
assert b_fail == 0, "baseline 有失敗測試，請調整分析文字"

# ---------- 要填入的內容 ----------
VALIDATION = (
    "（依 docs/spec.md 第 5 節）name 必填、必須是字串，去除前後空白後長度 1～100 字元，不可空白、不可含控制字元；"
    "model_url 必填，只接受 http/https、必須有主機名稱、port 須為 1～65535、長度不超過 2048 且不可含空白；"
    "position、rotation、scale 必須是含 x、y、z 三個分量的物件，分量須為有限數值（拒絕字串、布林、null、NaN、Infinity），"
    "position 每個分量介於 ±1,000,000、rotation 介於 ±360 度、scale 必須大於 0 且不超過 10,000；"
    "頂層與向量內都不允許額外欄位（傳入 id、created_at 也回 422）；id 必須是 UUID 格式，格式錯誤回 422、不存在回 404；"
    "GET /objects 的 limit 為 1～100、offset ≥ 0；驗證失敗一律回 422 且不寫入資料庫。"
)

ANALYSIS = (
    f"Part B 由 3 個 db-evaluator 並行評估，實際只花 {partB_par} 秒就收齊 JSON，token 僅 {n(tokB)}；"
    f"但整體來看，團隊版（階段 1＋2，可與單一 Agent 比較的範圍）共用 {n(team_cmp_tok)} token、{team_cmp_time} 秒，"
    f"單一 Agent 用 {n(btok)} token、{bdur:.0f} 秒；兩者 token 總量接近（團隊版約 {ratio_tok:.2f} 倍），"
    f"但團隊版的 input＋output 約為 {io_ratio:.1f} 倍、費用約 {cost_ratio:.1f} 倍、時間約 {ratio_time:.1f} 倍。"
    "原因是每個子代理都要重新建立 context、重新讀規格與程式碼，派工之間也是依序等待；"
    "單一 Agent 一個 context 用到底，token 有 93% 是便宜的 cache 讀取，後期 context 變長並沒有讓它失敗，但它自行擴充了規格"
    "（rotation 改成四元數、加了 PATCH，且沒有作業指定的 model_url 欄位），偏離了作業需求。"
    f"品質方面，團隊版依規格實作，{t_pass} 個測試全部通過，且 reviewer 找到 2 項測試沒抓到的規格不符；單一 Agent 版 {b_pass} 個測試全部通過"
    + (f"、{b_fail} 個失敗" if b_fail else "")
    + "。註：團隊版 token 為子代理加總，不含主 Agent 本身；單一 Agent 版沒有分段紀錄，Part B 與 Part C 合併計算。"
)

BEST = (
    "reviewer。它只有 Read、Grep、Glob 三個工具，82.9 秒、48,242 token 就完成審查，沒有任何權限被拒，"
    "而且找出 tester 184 個測試都沒抓到的 2 項規格不符：送出非 UTF-8 的 body 會回 400（規格要求 422），"
    "以及 /objects/ 會 307 轉址而不是回統一格式的 404；交回 coder 修正後，tester 補了對應測試，最後 191 個測試全部通過。"
)
WORST = (
    "coder。第一次實作（序號 5）用了 21 個 turns、455,263 token，是所有子代理中最多的；"
    "它兩次想把暫存驗證腳本寫到系統 scratchpad，都被 guard_paths.py hook 擋下（只能寫 app/ 與 requirements.txt），"
    "另外有 4 次 Bash 指令因為用了 heredoc 或「DATABASE_URL=... python」這種環境變數前綴寫法，不符合允許的 Bash(python:*) 而被拒，"
    "最後改把暫存腳本放進 app/_smoke_check.py 跑完再刪除，等於繞了一圈。"
)
ADJUST = (
    "實際做過的調整：(1) 一開始用 session 內建的 Agent 工具載入不到自訂子代理，改成以 claude -p --agent <名稱> 執行，"
    "並先做一次前置測試，確認 tester 寫 app/hooktest.py 會被 hook 擋下；"
    "(2) 測試 hook 時發現收到無法解析的輸入會直接放行，改成 fail-closed（一律擋下），並把錯誤訊息改成 UTF-8 輸出；"
    "(3) 依 coder 回報「只覆寫 get_db 仍會產生 xr_objects.db」，在派給 tester 的任務中要求先設定 DATABASE_URL=sqlite:// 再 import app，"
    "結果測試全程沒有產生資料庫檔案；(4) 依 reviewer 的低嚴重度問題派 coder 修正 1 輪，再請 tester 補測。"
    "建議（尚未實作）：在 guard_paths.py 為 coder 增加一個專用暫存資料夾（例如 .scratch/），"
    "並在 coder 的 prompt 註明「驗證請用 python -c 或 python -m，不要用環境變數前綴」，以減少 coder 被擋下與繞路所浪費的 token。"
)
SECURITY = (
    f"security-auditor 依 OWASP Top 10 (2021) 逐項審查 app/（{runs[10]['duration_ms'] / 1000:.1f} 秒、{n(tok3)} token），"
    "結果 0 項高、0 項中嚴重度：全面使用 SQLAlchemy ORM 參數化查詢（無 SQL 注入）、Pydantic 嚴格驗證並禁止額外欄位、"
    "model_url 只允許 http/https、錯誤回應不洩漏堆疊與輸入內容；A02、A07、A10 不適用。"
    "低嚴重度建議包括：對外部署前為寫入端點加 API Key（A01）、限制 body 大小與速率（A04）、"
    "產生套件鎖定檔並用 pip-audit 掃描（A06）、為寫入操作加稽核日誌（A09）。因沒有高、中嚴重度問題，未交給 coder 修改，"
    f"最終 python -m pytest -v 為 {t_pass} passed。詳見 docs/security.md。"
)

# ---------- 文件操作 ----------
d = docx.Document(SRC)


def is_hl(r):
    return r.font.highlight_color is not None


def set_text(run, text, keep_highlight=False):
    run.text = text
    if not keep_highlight:
        rpr = run._element.rPr
        for h in rpr.findall(qn("w:highlight")):
            rpr.remove(h)


def fill_par(p, values, keep_highlight=False):
    """把段落中的螢光 run 依序換成 values（list）。"""
    hl = [r for r in p.runs if is_hl(r)]
    assert len(hl) == len(values), (p.text, len(hl), len(values))
    for r, v in zip(hl, values):
        set_text(r, v, keep_highlight)


def par_with(text, occurrence=0):
    ps = [p for p in d.paragraphs if text in p.text]
    return ps[occurrence]


fill_par(par_with("繳交日期"), [TODAY])
fill_par(par_with("GitHub repo 連結"), [GITHUB])

# Part B 比較表
tb = d.tables[2]
for i, r in enumerate(evals, 1):
    row = tb.rows[i]
    s = r["scores"]
    vals = [r["db"], str(s["setup"]), str(s["python"]), str(s["testing"]), str(s["data_fit"]), str(s["scalability"]), str(r["total"])]
    tmpl = [x for x in row.cells[1].paragraphs[0].runs][0]
    for c, v in zip(row.cells[1:], vals):
        p = c.paragraphs[0]
        hl = [x for x in p.runs if is_hl(x)]
        if hl:
            set_text(hl[0], v)
        else:
            new = copy.deepcopy(tmpl._element)
            p._p.append(new)
            run = p.runs[-1]
            set_text(run, v)
        p.alignment = row.cells[0].paragraphs[0].alignment
    assert row.cells[0].paragraphs[0].text.strip() == str(i)

fill_par(par_with("我的選擇與理由"), [choice])
fill_par(par_with("輸入驗證規則"), [VALIDATION])
fill_par(par_with("測試總數"), [str(t_total), str(t_pass), str(t_fail)])
fill_par(par_with("貼上 pytest -v"), ["（截圖）"], keep_highlight=True)
for p in d.paragraphs:
    if any(is_hl(r) and "貼上截圖" in r.text for r in p.runs):
        fill_par(p, ["（截圖）"], keep_highlight=True)
fill_par(par_with("圖 2"), ["coder（序號 5，第一次實作）"])
fill_par(par_with("圖 3"), ["tester（序號 6，撰寫並執行 pytest）"])

# 6.1 比較表
t61 = d.tables[4]
cells = {
    1: (f"未分段（B、C 由同一個 session 連續完成，合計見下一列）", f"{partB_time} 秒（3 個 db-evaluator 並行實際 {partB_par} 秒；已扣除等待登入 CLI 的 {blocked} 秒）"),
    2: ("未分段（合計見下一列）", f"{n(tokB)}（3 個 db-evaluator 加總）"),
    3: (f"Part B＋C 合計 {bdur:.1f} 秒（duration_ms＝{b.get('duration_ms')}）", f"{partC_time} 秒（階段 2 時間戳相減）"),
    4: (f"Part B＋C 合計 {n(btok)}（usage 加總）", f"{n(tokC)}（architect、coder×2、tester×2、reviewer 加總）"),
    5: (f"{b_pass} passed" + (f"／{b_fail} failed" if b_fail else ""), f"{t_pass} passed／{t_fail} failed"),
}
for ri, (single, team) in cells.items():
    row = t61.rows[ri]
    fill_par(row.cells[1].paragraphs[0], [single])
    fill_par(row.cells[2].paragraphs[0], [team])

# 6.1 比較方式的說明改為實際做法（原文寫 /cost，但本次實際以 JSON usage 與 date +%s 記錄）
p = par_with("比較方式")
for r in p.runs:
    if "/cost" in r.text:
        r.text = r.text.replace("以 Claude Code 的 /cost 記錄數據。",
                                "數據取自 Claude Code 無頭模式 JSON 結果中的 duration_ms 與 usage（token＝input＋output＋cache 建立＋cache 讀取），團隊版耗時以 date +%s 時間戳相減，詳見 docs/run-log.md。")
assert "/cost" not in p.text, p.text

fill_par(par_with("分析："), [ANALYSIS])
fill_par(par_with("表現最好"), [BEST])
fill_par(par_with("表現最差"), [WORST])
fill_par(par_with("我的調整"), [ADJUST])
fill_par([p for p in d.paragraphs if any(is_hl(r) and "3～5 句" in r.text for r in p.runs)][0], ["（心得待填）"], keep_highlight=True)
fill_par(par_with("審查結果"), [SECURITY])

# 檢查：剩下的螢光只能是（截圖）與（心得待填），且不能殘留【】
left = []
for p in list(d.paragraphs) + [pp for t in d.tables for row in t.rows for c in row.cells for pp in c.paragraphs]:
    for r in p.runs:
        if is_hl(r):
            left.append(r.text)
        assert "【" not in r.text, r.text
print("剩下的螢光：", left)
d.save(DST)
print("已輸出", DST)
