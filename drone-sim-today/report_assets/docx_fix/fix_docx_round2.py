# -*- coding: utf-8 -*-
"""Second pass over UW-TIG_Project_Work_Report_final.docx:
  * two sentences that were split across paragraphs (Section 6.2 and 6.9) are joined and cleaned
  * the Table 6.7 caption gets the same caption format as the others
  * the appendices' code listings (garbled with letter spacing by the PDF-to-Word conversion) are
    re-inserted from the repository source in Courier New, line by line.
"""
import ast
import os
import textwrap

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "UW-TIG_Project_Work_Report_final.docx")
d = docx.Document(DOC)


def P():
    return d.paragraphs


def find(prefix):
    for p in P():
        if p.text.strip().startswith(prefix):
            return p
    raise KeyError(prefix)


def set_text(p, text):
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def delete(p):
    p._p.getparent().remove(p._p)


def body_fmt(p):
    p.style = d.styles["Body Text"]
    pf = p.paragraph_format
    pf.left_indent, pf.first_line_indent, pf.line_spacing = 75565, 359410, 1.3
    p.alignment = AL.JUSTIFY


# ---- Section 6.2 (development progression): one paragraph
p1 = find("Development progression")
p2 = [p for p in P() if p.text.startswith("0.88 / 0.78 / 0.82")][0]
p3 = [p for p in P() if p.text.startswith("0.99 / 0.97. The truth")][0]
set_text(p1, "Development progression (precision / recall / F1): original 0.76 / 0.63 / 0.65; fixes 1–3 0.88 / 0.78 / 0.82; plus the survey "
             "standoff 0.86 / 0.96 / 0.90; plus the on-wall check 0.95 / 0.99 / 0.97. Much of the gain is therefore measurement, not planning: "
             "under the old scoring formula the final UW-TIG precision on the test seeds would be 0.668.")
body_fmt(p1)
delete(p2)
delete(p3)

# ---- Section 6.9: one paragraph
q1 = find("The ordering mostly survives")
q2 = [p for p in P() if p.text.startswith("+0.003 to +0.035")][0]
head = q1.text.rstrip()
set_text(q1, head + " +0.003 to +0.035, excluding zero, winning 3 of 5 seeds) and far ahead of random search (+0.120, all 5 seeds). "
             "What UW-TIG keeps is cost: it flies 480 m, against 860 m for IPP, 570 m for the latency rule and 2,396 m for random search. "
             "In this yard UW-TIG therefore ties for the best detection score at a lower flight cost, rather than winning outright.")
delete(q2)

# ---- Table 6.7 caption
cap = find("Table 6.7 UW-TIG minus each planner")
set_text(cap, cap.text.strip())
cap.style = d.styles["Normal"]
cap.alignment = AL.CENTER
cap.paragraph_format.left_indent = None
cap.paragraph_format.first_line_indent = None
cap.paragraph_format.keep_with_next = True
for r in cap.runs:
    r.font.size = Pt(10.5); r.font.name = "Times New Roman"; r.bold = False


# ---- appendices: re-paste code
def get_src(relpath, names):
    src = open(os.path.join(ROOT, relpath), encoding="utf-8").read()
    lines = src.splitlines()
    out = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            out.append("\n".join(lines[node.lineno - 1: node.end_lineno]))
    return "\n\n".join(out)


SOURCES = {
    "Appendix A": ("planning/planners.py", {"UWTIGPlanner"}),
    "Appendix B": ("planning/planners.py", {"MissionBelief"}),
    "Appendix C": ("geometry.py", {"localize_on_wall", "wall_plane", "ray_plane_intersect"}),
    "Appendix D": ("memory/store_mem.py", {"InMemoryStore"}),
}
WRAP = 96


def make_code_par(anchor_p, text):
    new = OxmlElement("w:p")
    anchor_p._p.addnext(new)
    par = Paragraph(new, anchor_p._parent)
    par.style = d.styles["Normal"]
    run = par.add_run(text if text else " ")
    run.font.name = "Courier New"
    rpr = run._r.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    for att in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(att), "Courier New")
    run.font.size = Pt(7)
    run.bold = False
    pf = par.paragraph_format
    pf.space_before = pf.space_after = Pt(0)
    pf.line_spacing = 1.0
    pf.left_indent = 0
    pf.first_line_indent = 0
    pf.right_indent = 0
    par.alignment = AL.LEFT
    pf.widow_control = False
    return par


paras = P()
a0 = [i for i, p in enumerate(paras) if p.text.strip() == "APPENDICES"][0]
heads = [(i, p) for i, p in enumerate(paras) if i > a0 and p.style.name.startswith("Heading") and p.text.strip().startswith("Appendix")]
for k, (i, h) in enumerate(heads):
    key = h.text.strip()[:10]
    end = heads[k + 1][0] if k + 1 < len(heads) else len(paras)
    # remove the old (garbled) listing between this heading and the next
    for p in paras[i + 1:end]:
        delete(p)
    rel, names = SOURCES[key]
    anchor = h
    n = 0
    for ln in get_src(rel, names).splitlines():
        ln = ln.replace("\t", "    ")
        indent = len(ln) - len(ln.lstrip(" "))
        pieces = textwrap.wrap(ln, WRAP, subsequent_indent=" " * (indent + 4), drop_whitespace=False, break_long_words=True) if len(ln) > WRAP else [ln]
        for piece in pieces or [""]:
            anchor = make_code_par(anchor, piece)
            n += 1
    print(key, "-> inserted", n, "lines from", rel)
d.save(DOC)
print("saved", DOC)
