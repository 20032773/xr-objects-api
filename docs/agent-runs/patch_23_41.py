"""只修改完成版報告的 2.3 與 4.1 兩處說明（就地修改，不影響已貼上的截圖或心得）。可重複執行。"""
import os
import sys

import docx

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST = os.path.join(ROOT, "XR作業_資工四甲_41218106_鐘仁澤_完成.docx")

NEW_23 = ("只預先允許 pytest 指令，其他 Bash 指令在互動模式下執行前都會詢問使用者。"
          "本次子代理以無頭模式（claude -p --agent）執行，無法跳出詢問，因此改為每次派工用 --allowedTools 明確指定該角色可用的工具"
          "（coder 可用 python、pip；tester 只能用 pytest；reviewer、security-auditor 只有讀檔工具），詳見 docs/run-log.md。")
NEW_41 = "取得場景物件列表（分頁：limit 預設 50、範圍 1～100，offset ≥ 0；回傳 items 與 total）"

d = docx.Document(DST)
p = next(p for p in d.paragraphs if p.text.startswith("settings.json："))
r = next(x for x in p.runs if "只預先允許 pytest 指令" in x.text)
r.text = NEW_23

t = next(t for t in d.tables if t.rows[0].cells[0].text.strip() == "方法")
c = t.rows[1].cells[2].paragraphs[0]
assert c.text in ("取得所有場景物件", NEW_41), c.text
c.runs[0].text = NEW_41
for extra in c.runs[1:]:
    extra.text = ""

d.save(DST)
print(p.text)
print(c.text)
