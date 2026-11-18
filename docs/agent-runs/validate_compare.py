"""驗證 db-evaluator 的 JSON 格式，依 total 排序並輸出 docs/compare.md。"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
KEYS = ["setup", "python", "testing", "data_fit", "scalability"]
def validate(r):
    errs = []
    if set(r) != {"db", "scores", "total", "pros", "cons", "recommended_library"}: errs.append(f"欄位不符: {sorted(r)}")
    s = r.get("scores", {})
    if set(s) != set(KEYS): errs.append("scores 欄位不符")
    for k in KEYS:
        v = s.get(k)
        if not (isinstance(v, int) and 1 <= v <= 5): errs.append(f"{k}={v} 不是 1～5 的整數")
    if sum(s.get(k, 0) for k in KEYS) != r.get("total"): errs.append("total 不等於五項加總")
    for k in ("pros", "cons"):
        if not (isinstance(r.get(k), list) and r[k] and all(isinstance(x, str) for x in r[k])): errs.append(f"{k} 不是非空字串陣列")
    if not isinstance(r.get("recommended_library"), str) or not r["recommended_library"]: errs.append("recommended_library 空白")
    return errs
results = []
for i in (1, 2, 3):
    d = json.load(open(f"docs/agent-runs/{i}-db-evaluator.json", encoding="utf-8"))
    try:
        r = json.loads(d["result"])
    except Exception as e:
        print(f"#{i} JSON 解析失敗: {e}"); sys.exit(1)
    errs = validate(r)
    print(f"#{i} {r.get('db')}: {'格式正確' if not errs else errs}")
    if errs: sys.exit(1)
    results.append(r)
# 依 total 由高到低；同分時依 testing、再依 python（本專案重視測試與 FastAPI 整合）
results.sort(key=lambda r: (r["total"], r["scores"]["testing"], r["scores"]["python"]), reverse=True)
L = ["# Part B：XR 場景物件管理 API 資料庫方案比較", "",
     "由 3 個 db-evaluator 子代理並行評估（各自只評估一個資料庫），主 Agent 驗證 JSON 格式後依總分排序。",
     "評分 1～5 分：安裝＝安裝設定難易度、Python＝Python/FastAPI 整合、測試＝pytest 測試方便度、資料適配＝與場景物件資料結構的適配、擴充＝未來擴充性。",
     "同分時依「測試」、再依「Python」分數排序。", "",
     "| 排名 | 資料庫 | 安裝 | Python | 測試 | 資料適配 | 擴充 | 總分 | 優點 | 缺點 | 建議套件 |",
     "|---|---|---|---|---|---|---|---|---|---|---|"]
for n, r in enumerate(results, 1):
    s = r["scores"]
    L.append(f"| {n} | {r['db']} | {s['setup']} | {s['python']} | {s['testing']} | {s['data_fit']} | {s['scalability']} | **{r['total']}** | "
             + "<br>".join("• " + p for p in r["pros"]) + " | " + "<br>".join("• " + c for c in r["cons"]) + f" | {r['recommended_library']} |")
top = results[0]
L += ["", "## 選擇與理由", "",
      f"選擇 **{top['db']}**（總分 {top['total']}，第 1 名），PostgreSQL 與 MongoDB 皆為 19 分。"
      f"{top['db']} 在安裝、Python 整合與測試三項都拿到滿分：Python 內建驅動、不需另外架設資料庫伺服器，pytest 可為每個測試建立隔離的暫存資料庫，最符合課堂作業單機開發與自動化測試的需求。"
      "它的缺點是寫入併發與水平擴充較弱，因此實作時透過資料存取層隔離資料庫細節，未來若要正式上線可再遷移到擴充性滿分的 PostgreSQL。", "",
      "原始 JSON：docs/agent-runs/1～3-db-evaluator.json"]
open("docs/compare.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("排序:", [(r["db"], r["total"]) for r in results])
