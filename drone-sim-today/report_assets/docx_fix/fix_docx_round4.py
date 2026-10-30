# -*- coding: utf-8 -*-
"""Fourth pass: adds the YOLOv8 size comparison (Section 6.1) and the planner-only tests (new Section 6.11) to the edited report."""
import copy, os
import docx
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(os.path.dirname(HERE)), "UW-TIG_Project_Work_Report_final.docx")
d = docx.Document(DOC)
ps = d.paragraphs


def find(prefix, style=None):
    return [p for p in d.paragraphs if p.text.strip().startswith(prefix) and (style is None or p.style.name == style)][0]


def clone_after(anchor_el, src_p, text):
    el = copy.deepcopy(src_p._p)
    anchor_el.addnext(el)
    p = docx.text.paragraph.Paragraph(el, src_p._parent)
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    return p


body_src = find("The detector is evaluated on the held-out", "Body Text")
cap_src = find("Table 6.1 Detector results", "Normal")
cap_src = [p for p in d.paragraphs if p.text.startswith("Table 6.1 Detector results") and "\t" not in p.text][0]
tbl_src = [t for t in d.tables if t.rows[0].cells[0].text.strip() == "Model"][0]
head_src = find("Does a Broader Detector", "Heading 2")
list_src = [p for p in d.paragraphs if p.style.name == "List Paragraph" and p.text.startswith("Selection-rule baselines")][0]

# ---- Section 6.1 additions, after the 'Crack is the hardest class' paragraph
anchor = find("Crack is the hardest class", "Body Text")
a = anchor._p
p1 = clone_after(a, body_src,
    "The rows above differ in resolution, epochs and data, so they are not a fair comparison of model size. YOLOv8n, v8s and v8m were therefore "
    "retrained with exactly the same recipe: the same fixed random subset of 4,000 MBDD2025 training images, 640 px, 30 epochs, batch 8, seed 0 and "
    "no oversampling, on one RTX 5060 GPU (datagen/compare_detectors.py). All three were scored on the full 1,448-image test split. YOLOv8l was not "
    "trained (8 GB of GPU memory). Each model was trained once, so differences of a few thousandths are within run-to-run noise.")
cap = clone_after(p1._p, cap_src, "Table 6.1b YOLOv8 size comparison under identical subset training (4,000 images, 30 epochs, 640 px)")
tel = copy.deepcopy(tbl_src._tbl)
cap._p.addnext(tel)
tbl = docx.table.Table(tel, anchor._parent)
rows = [["Model", "mAP50", "mAP50-95", "Precision", "Recall"],
        ["YOLOv8n (3.0 M parameters)", "0.743", "0.373", "0.786", "0.681"],
        ["YOLOv8s (11.1 M)", "0.793", "0.411", "0.803", "0.740"],
        ["YOLOv8m (25.8 M)", "0.796", "0.418", "0.802", "0.744"]]
for extra in tbl.rows[len(rows):]:
    extra._tr.getparent().remove(extra._tr)
for r, vals in zip(tbl.rows, rows):
    for c, v in zip(r.cells, vals):
        par = c.paragraphs[0]
        if par.runs:
            par.runs[0].text = v
            for x in par.runs[1:]:
                x._r.getparent().remove(x._r)
        else:
            par.add_run(v)
        for extra in c.paragraphs[1:]:
            extra._p.getparent().remove(extra._p)
p2 = clone_after(tel, body_src,
    "Going from n to s gives +0.050 mAP50; going from s to m gives only +0.003, which is inside run-to-run noise, for 2.3 times the parameters. "
    "YOLOv8s is therefore the sensible default: nearly all of the gain from model size is reached at the small size. These subset-trained scores "
    "(0.74 to 0.80) are lower than the default detector’s 0.884 because that model saw all 12,955 training images for 100 epochs.")

# ---- new Section 6.11 before 'Threats to Validity'
thr = find("Threats to Validity", "Heading 2")
t = thr._p
h = copy.deepcopy(head_src._p)
t.addprevious(h)
hp = docx.text.paragraph.Paragraph(h, head_src._parent)
hp.runs[0].text = "Planner-Only Tests: Oracle Detector, Weight Sensitivity and Ten Seeds"
for r in hp.runs[1:]:
    r._r.getparent().remove(r._r)


def before_thr(src, text):
    el = copy.deepcopy(src._p)
    t.addprevious(el)
    p = docx.text.paragraph.Paragraph(el, src._parent)
    p.runs[0].text = text
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)


before_thr(body_src,
    "Section 6.4 found that switching off the uncertainty and growth terms changes nothing. Two explanations remain: the real detector gives too weak a signal, "
    "or the terms are too weak at their weights (1.5 and 2.0). Both were tested. An oracle detector (perception/oracle_detector.py) reads the scenario’s "
    "ground truth and returns detections with controlled noise: 15% misses, confidence rising with severity, faint defects more uncertain, and defects that really "
    "grow. It is a synthetic planner-only test and says nothing about real detection quality.")
for txt in [
    "Oracle detector, both yards, 5 seeds. The no-uncertainty and no-growth variants are identical to full UW-TIG in route and F1 (9 walls: 124.6 m; 31 walls: "
    "480 m, F1 0.871 against 0.870 and 0.871). In the growing scenario every variant detects the growth (fraction 1.0), including the one without the growth term, "
    "because the coverage and revisit logic already finds it.",
    "Weight sensitivity. Setting both weights to 0, 6 and 20 leaves F1 unchanged (9 walls: 0.918 in all three; 31 walls: 0.822, 0.821, 0.820). The terms do not "
    "change the route even when they dominate the score.",
    "Staleness and lookahead. Without them the flight is shorter (9 walls: 80.6 m against 124.9 m; 31 walls, oracle: 407 and 445 m against 480 m). With the real "
    "detector F1 is unchanged over ten seeds (0.933); with the oracle it falls slightly (31 walls: 0.862 and 0.864 against 0.871). These two terms add flight "
    "cost rather than detection quality in this simulator.",
    "Ten seeds, 9-wall yard, real detector (seeds 0 to 9). UW-TIG 0.933 F1 at 124.9 m; Alamdari 0.922 at 168 m; Rückin 0.911 at 218 m; GATSBI 0.905; random "
    "0.860 at 379 m; Bircher 0.813; Isler 0.655; no coverage phase 0.676. UW-TIG minus Rückin is +0.022 (95% CI −0.002 to +0.055) and minus Alamdari "
    "+0.011 (−0.003 to +0.027): ahead on average but not significantly. The 31-wall ten-seed run was not completed."]:
    before_thr(list_src, txt)
before_thr(body_src,
    "Conclusion of these tests: the coverage-first phase and cost-aware routing carry UW-TIG’s results. The uncertainty and growth terms, the parts that make "
    "the planner uncertainty-weighted and temporal, show no measurable benefit in this simulator and are reported as untested extensions, not as demonstrated contributions.")
d.save(DOC)
print("saved")
