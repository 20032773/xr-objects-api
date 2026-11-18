"""讀取 docs/agent-runs/*.json，印出每次子代理執行的耗時與 token。"""
import json, sys, glob, os
sys.stdout.reconfigure(encoding="utf-8")
def tok(u):
    return {k: u.get(k, 0) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}
rows = []
for f in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "*.json")), key=lambda p: int(os.path.basename(p).split("-")[0])):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print(os.path.basename(f), "INVALID", e); continue
    t = tok(d.get("usage", {})); total = sum(t.values())
    rows.append((os.path.basename(f), d.get("duration_ms"), d.get("num_turns"), t, total, d.get("total_cost_usd"), d.get("is_error")))
    print(os.path.basename(f), "dur_ms=", d.get("duration_ms"), "turns=", d.get("num_turns"), t, "total=", total, "cost=", d.get("total_cost_usd"), "err=", d.get("is_error"))
print("SUM total tokens =", sum(r[4] for r in rows), " SUM in+out =", sum(r[3]["input_tokens"] + r[3]["output_tokens"] for r in rows), " SUM cost =", round(sum(r[5] or 0 for r in rows), 4), " SUM dur_ms =", sum(r[1] or 0 for r in rows))
