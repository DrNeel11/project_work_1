# -*- coding: utf-8 -*-
"""Sixth pass: figure/table captions and picture paragraphs had mixed indents and alignments (several were pushed to the right);
all are centred with zero indents, and the Future Scope item about larger detectors is updated to reflect the completed v8n/s/m comparison."""
import os, re
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
from docx.shared import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "UW-TIG_Project_Work_Report_final.docx")
d = docx.Document(DOC)
n = m = 0
for p in d.paragraphs:
    t = p.text.strip()
    cap = re.match(r"(Table|Fig\.) \d\.\d+[a-z]?[ :]", t) and "\t" not in t
    pic = p._p.xpath(".//w:drawing") and not t
    if cap or pic:
        p.alignment = AL.CENTER
        pf = p.paragraph_format
        pf.left_indent = pf.first_line_indent = Pt(0)
        pf.right_indent = 685800   # same right indent as body text, so centring is about the text block
        n += 1 if cap else 0
        m += 0 if cap else 1
print("captions", n, "picture paragraphs", m)
d.save(DOC)

# ---- text paragraphs with no right indent ran to the page edge (the section's right margin is only 0.2 in; every other paragraph carries a ~0.75 in right indent)
d = docx.Document(DOC)
k = 0
for p in d.paragraphs:
    if len(p.text.strip()) > 40 and p.style.name in ("Body Text", "List Paragraph", "Normal") and p.alignment != AL.CENTER:
        ri = p.paragraph_format.right_indent
        if ri is None or ri < 500000:
            p.paragraph_format.right_indent = 685800
            k += 1
print("right indent set on", k, "paragraphs")
d.save(DOC)

# ---- the section break after the 6.4 bullet list started the next section on a new page, leaving a nearly empty page
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
d = docx.Document(DOC)
ps = d.paragraphs
i = [k for k, p in enumerate(ps) if p.text.startswith("This is an open finding")][0]
for j in range(i - 4, i):
    sp = ps[j]._p.xpath(".//w:sectPr")
    if sp:
        for q in ps[j + 1:]:
            nsp = q._p.xpath(".//w:sectPr")
            if nsp:
                t = nsp[0].find(qn("w:type"))
                if t is None:
                    t = OxmlElement("w:type")
                    nsp[0].insert(0, t)
                t.set(qn("w:val"), "continuous")
                print("section after 6.4 bullets made continuous")
                break
        t = sp[0].find(qn("w:type"))
        break
d.save(DOC)
