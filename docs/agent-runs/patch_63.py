"""把 6.3 心得的「（心得待填）」換成草稿並拿掉螢光（就地修改，不影響已貼上的截圖）。"""
import os
import sys

import docx
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST = os.path.join(ROOT, "XR作業_資工四甲_41218106_鐘仁澤_完成.docx")

TEXT = (
    "這次讓主 Agent 當 Tech Lead 並把工作分給不同子代理，我最大的收穫是發現權限不能只寫在 prompt 裡，"
    "coder 兩次想把暫存腳本寫到 app 以外的地方都被 hook 擋下來，可見用工具白名單加上 hook 強制執行才可靠。"
    "分工也讓品質變好，tester 的 184 個測試全部通過，反而是只能讀檔的 reviewer 找出兩個不符合規格的地方。"
    "不過團隊版花的時間大約是單一 Agent 的 3 倍，費用也多了 2.6 倍，而單一 Agent 雖然比較快，卻自己改了規格還漏掉 model_url 欄位。"
    "下次我會先把規格寫得更清楚，也會給 coder 一個專用的暫存資料夾，減少它被擋下後繞路浪費的 token。"
)

d = docx.Document(DST)
runs = [r for p in d.paragraphs for r in p.runs if r.text == "（心得待填）"]
assert len(runs) == 1, f"找到 {len(runs)} 個「（心得待填）」"
r = runs[0]
r.text = TEXT
for h in r._element.rPr.findall(qn("w:highlight")):
    r._element.rPr.remove(h)
d.save(DST)
print("已填入 6.3 心得")
