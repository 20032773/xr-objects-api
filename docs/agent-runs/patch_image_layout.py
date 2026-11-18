"""修正截圖版面：貼上時圖片被併進下一段（標題或圖說同一行），把每張圖移到自己的段落。

- 圖片原本在某段落開頭 → 在該段落「前面」插入一個新的置中段落放圖片，原段落只留文字。
- 執行前會先備份成 *_備份.docx。可重複執行（已獨立的圖片段落不會再動）。
"""
import copy
import os
import shutil
import sys

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST = os.path.join(ROOT, "XR作業_資工四甲_41218106_鐘仁澤_完成.docx")
BAK = DST.replace("_完成.docx", "_完成_備份.docx")
shutil.copyfile(DST, BAK)

d = docx.Document(DST)
moved = 0
for p in list(d.paragraphs):
    runs = [r for r in p._p.findall(qn("w:r"))]
    img_runs = [r for r in runs if r.findall(".//" + qn("a:blip"))]
    if not img_runs:
        continue
    has_text = any("".join(t.text or "" for t in r.findall(qn("w:t"))).strip() for r in runs if r not in img_runs)
    if not has_text:
        continue  # 已經是獨立的圖片段落
    new_p = copy.deepcopy(p._p)
    for child in list(new_p):
        if child.tag != qn("w:pPr"):
            new_p.remove(child)
    # 圖片段落一律用內文樣式、置中，避免變成標題
    ppr = new_p.find(qn("w:pPr"))
    if ppr is not None:
        for tag in ("w:pStyle", "w:numPr", "w:outlineLvl"):
            for el in ppr.findall(qn(tag)):
                ppr.remove(el)
    for r in img_runs:
        p._p.remove(r)
        new_p.append(r)
    p._p.addprevious(new_p)
    np_ = docx.text.paragraph.Paragraph(new_p, p._parent)
    np_.alignment = WD_ALIGN_PARAGRAPH.CENTER
    moved += len(img_runs)
    print(f"已把 {len(img_runs)} 張圖移出：{p.text[:30]}")

d.save(DST)
print(f"完成，共移動 {moved} 張圖；備份：{BAK}")
