# -*- coding: utf-8 -*-
"""Builds the project-work dissertation PDF (department format: cover, bona
fide, certificate, contents, acknowledgement, synopsis, lists, chapters 1-8,
bibliography, appendices). Numbers come from results/comparison.csv; source
excerpts in the appendices are read from the repository at build time.
Run from drone-sim-today/:  venv python report_assets/build_dissertation.py"""
import ast
import csv
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGS = os.path.join(HERE, "dissertation_figs")
OUT_PATH = os.path.join(ROOT, "UW-TIG_Project_Work_Report.pdf")

# ---------------------------------------------------------------- fonts
F = r"C:\Windows\Fonts"
pdfmetrics.registerFont(TTFont("Times", os.path.join(F, "times.ttf")))
pdfmetrics.registerFont(TTFont("Times-B", os.path.join(F, "timesbd.ttf")))
pdfmetrics.registerFont(TTFont("Times-I", os.path.join(F, "timesi.ttf")))
pdfmetrics.registerFont(TTFont("Times-BI", os.path.join(F, "timesbi.ttf")))
pdfmetrics.registerFont(TTFont("Cour", os.path.join(F, "cour.ttf")))
pdfmetrics.registerFontFamily("Times", normal="Times", bold="Times-B", italic="Times-I", boldItalic="Times-BI")

# ---------------------------------------------------------------- data
rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "comparison.csv"))))
MAIN = [r for r in rows if r["scenario"] != "growing"]


def M(planner, col, scen=None):
    rs = [r for r in MAIN if r["planner"] == planner and (scen is None or r["scenario"] in scen)]
    v = [float(r[col]) for r in rs if r[col] not in ("", "nan")]
    return sum(v) / len(v) if v else float("nan")


f3 = lambda v: f"{v:.3f}"
f2 = lambda v: f"{v:.2f}"
f1 = lambda v: f"{v:.1f}"
import json as _json
SC = _json.load(open(os.path.join(ROOT, "results", "scaleup_summary.json")))
DET = _json.load(open(os.path.join(ROOT, "results", "detector_extra.json")))


def SP(name, p, k):
    return SC[name]["planners"][p][k]


def SD(name, p):
    d = SC[name]["uwtig_vs"][p]
    return d["mean_diff"], d["ci"][0], d["ci"][1], d["seeds_won"], d["n"]

TITLE = "UW-TIG: Uncertainty-Weighted Temporal Information Gain for Closed-Loop Defect Inspection"
SUBTITLE = "A Novel Active-Reinspection Planner and Its Simulation Testbed"
TEAM = [("Akhil Ramalingam", "23Z207"), ("Anbuchandiran K", "23Z209"), ("Neelesh Padmanabh", "23Z241"),
        ("Saumiyaa Sri V L", "23Z261"), ("Sowndarya Elangi S", "23Z269"), ("Therdhana J P", "23Z273")]
GUIDE, COGUIDE = "Ms. L. Karthika", "Dr. N. Gopika Rani"
COURSE = "23Z711 - PROJECT WORK 1"
DATE = "NOVEMBER 2026"

# ---------------------------------------------------------------- styles
base = dict(fontName="Times", fontSize=12, leading=18, textColor=colors.black)
S = {
    "body": ParagraphStyle("body", alignment=TA_JUSTIFY, firstLineIndent=1.0 * cm, spaceAfter=7, **base),
    "bodyni": ParagraphStyle("bodyni", alignment=TA_JUSTIFY, spaceAfter=7, **base),
    "bullet": ParagraphStyle("bullet", alignment=TA_JUSTIFY, leftIndent=1.1 * cm, bulletIndent=0.4 * cm, spaceAfter=3, **base),
    "chap": ParagraphStyle("chap", fontName="Times-B", fontSize=18, leading=24, alignment=TA_CENTER, spaceBefore=14, spaceAfter=14),
    "sec": ParagraphStyle("sec", fontName="Times-B", fontSize=13.5, leading=19, spaceBefore=10, spaceAfter=5),
    "sub": ParagraphStyle("sub", fontName="Times-B", fontSize=12, leading=17, spaceBefore=6, spaceAfter=3),
    "cap": ParagraphStyle("cap", fontName="Times", fontSize=10.5, leading=14, alignment=TA_CENTER, spaceBefore=3, spaceAfter=12),
    "tcap": ParagraphStyle("tcap", fontName="Times", fontSize=10.5, leading=14, alignment=TA_CENTER, spaceBefore=8, spaceAfter=4, keepWithNext=1),
    "center": ParagraphStyle("center", alignment=TA_CENTER, **base),
    "centerb": ParagraphStyle("centerb", alignment=TA_CENTER, **dict(base, fontName="Times-B")),
    "front": ParagraphStyle("front", fontName="Times-B", fontSize=16, leading=22, alignment=TA_CENTER, spaceBefore=6, spaceAfter=16),
    "cell": ParagraphStyle("cell", fontName="Times", fontSize=9.5, leading=11.5),
    "cellc": ParagraphStyle("cellc", fontName="Times", fontSize=9.5, leading=11.5, alignment=TA_CENTER),
    "cellh": ParagraphStyle("cellh", fontName="Times-B", fontSize=9.5, leading=11.5, alignment=TA_CENTER),
    "code": ParagraphStyle("code", fontName="Cour", fontSize=7.2, leading=8.6),
    "ref": ParagraphStyle("ref", alignment=TA_JUSTIFY, leftIndent=1.0 * cm, firstLineIndent=-1.0 * cm, spaceAfter=5,
                          **dict(base, fontSize=11, leading=15)),
}

story = []
HDR = {"left": "", "right": ""}
BODY_START = {"page": None}
FRONT_START = {"page": None}
_CACHE = os.path.join(HERE, ".dissertation_pages.json")
if os.path.exists(_CACHE):  # page offsets from the previous full build (run the script twice)
    import json
    _c = json.load(open(_CACHE))
    BODY_START["page"], FRONT_START["page"] = _c.get("body"), _c.get("front")


def P(t):
    story.append(Paragraph(t, S["body"]))


def PN(t):
    story.append(Paragraph(t, S["bodyni"]))


def B(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="\u2022"))
    story.append(Spacer(1, 4))


def H1(num, text, header_left):
    story.append(SetHeader(header_left, f"Chapter {num}"))
    story.append(PageBreak())
    story.append(Paragraph(f"{num}.&nbsp;&nbsp;{text.upper()}", S["chap"]))


def H2(text):
    story.append(Paragraph(text, S["sec"]))


def H3(text):
    story.append(Paragraph(text, S["sub"]))


class SetHeader(Flowable):
    def __init__(self, left, right):
        super().__init__()
        self.left, self.right = left, right

    def wrap(self, w, h):
        HDR["left"], HDR["right"] = self.left, self.right
        return 0, 0

    def draw(self):
        pass


class Mark(Flowable):
    """Records the physical page where a section of the book starts."""
    def __init__(self, store):
        super().__init__()
        self.store = store

    def wrap(self, w, h):
        return 0, 0

    def draw(self):
        self.store["page"] = self.canv.getPageNumber()


FIGREG, TABREG = [], []


def FIG(path, width, num, caption, border=False):
    img = Image(path, width=width, height=width * _ratio(path))
    story.append(KeepTogether([img, Paragraph(f"Fig. {num} {caption}", S["cap"])]))


def _ratio(path):
    from PIL import Image as PI
    w, h = PI.open(path).size
    return h / w


def TABLE(num, caption, header, data, colw, left=(0,), small=False, bold_row=None):
    cs = S["cell"]
    hdr = [Paragraph(h, S["cellh"]) for h in header]
    body = []
    for r in data:
        body.append([Paragraph(str(c), cs if i in left else S["cellc"]) for i, c in enumerate(r)])
    t = Table([hdr] + body, colWidths=colw, repeatRows=1)
    st = [("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if bold_row is not None:
        st.append(("BACKGROUND", (0, bold_row + 1), (-1, bold_row + 1), colors.HexColor("#f2f2f2")))
    t.setStyle(TableStyle(st))
    story.append(Paragraph(f"Table {num} {caption}", S["tcap"]))
    story.append(t)
    story.append(Spacer(1, 10))


# ---------------------------------------------------------------- doc template
class FigList(TableOfContents):
    def __init__(self, kind, **kw):
        super().__init__(**kw)
        self.kind = kind

    def notify(self, kind, stuff):
        if kind == self.kind:
            self.addEntries([stuff])


class Doc(BaseDocTemplate):
    def afterFlowable(self, fl):
        if not isinstance(fl, Paragraph):
            return
        pg = self.canv.getPageNumber()
        name, txt = fl.style.name, fl.getPlainText().replace(chr(160), " ")
        if name == "front" and txt.startswith("ACKNOWLEDGEMENT"):
            FRONT_START["page"] = pg
        if name == "chap" and txt.startswith("1."):
            BODY_START["page"] = pg
        shown = pg - ((BODY_START["page"] or 10 ** 6) - 1)
        if name == "chap":
            self.notify("TOCEntry", (0, txt, shown))
        elif name == "sec":
            self.notify("TOCEntry", (1, txt, shown))
        elif name == "cap" and txt.startswith("Fig."):
            n, _, c = txt.partition(" ")[2].partition(" ")
            self.notify("FigEntry", (0, "Fig. " + n + "\t" + c, shown))
        elif name == "tcap" and txt.startswith("Table"):
            n, _, c = txt.partition(" ")[2].partition(" ")
            self.notify("TabEntry", (0, "Table " + n + "\t" + c, shown))


ROMAN = ["", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]


def on_front(canv, doc):
    pass  # page numbers are stamped after the build (see stamp_page_numbers)


def on_body(canv, doc):
    canv.saveState()
    canv.setFont("Times", 10)
    canv.drawString(2.2 * cm, A4[1] - 1.5 * cm, HDR["left"])
    canv.drawRightString(A4[0] - 2.2 * cm, A4[1] - 1.5 * cm, HDR["right"])
    canv.restoreState()


doc = Doc(OUT_PATH, pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.2 * cm, topMargin=2.4 * cm, bottomMargin=2.3 * cm,
          title=TITLE, author="; ".join(n for n, _ in TEAM))
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate(id="front", frames=[frame], onPage=on_front),
                      PageTemplate(id="body", frames=[frame], onPage=on_body)])

# ================================================================ COVER
story.append(Paragraph(f"<b>{COURSE}</b>", ParagraphStyle("c0", alignment=TA_CENTER, **dict(base, fontSize=14))))
story.append(Spacer(1, 1.0 * cm))
story.append(Paragraph(f"<b>{TITLE}</b>", ParagraphStyle("c1", alignment=TA_CENTER, **dict(base, fontSize=17, leading=23))))
story.append(Spacer(1, 0.25 * cm))
story.append(Paragraph(f"<i>{SUBTITLE}</i>", ParagraphStyle("c1b", alignment=TA_CENTER, **dict(base, fontSize=13))))
story.append(Spacer(1, 0.9 * cm))
t = Table([[n, f"(Roll No: {r})"] for n, r in TEAM], colWidths=[5.2 * cm, 4.0 * cm])
t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Times", 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
story.append(t)
story.append(Spacer(1, 1.0 * cm))
for line in ["Dissertation submitted in partial fulfillment of the requirements for the degree of"]:
    story.append(Paragraph(line, S["center"]))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("<b>BACHELOR OF ENGINEERING</b>", S["center"]))
story.append(Paragraph("<b>Branch : COMPUTER SCIENCE and ENGINEERING</b>", S["center"]))
story.append(Paragraph("of Anna University", S["center"]))
story.append(Spacer(1, 0.5 * cm))
logo = Image(os.path.join(FIGS, "psg_logo.png"), width=3.6 * cm, height=3.6 * cm * 192 / 146)
logo.hAlign = "CENTER"
story.append(logo)
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(DATE, S["center"]))
story.append(Spacer(1, 0.7 * cm))
story.append(Paragraph("<b>DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING<br/>PSG COLLEGE OF TECHNOLOGY</b>", S["center"]))
story.append(Spacer(1, 0.2 * cm))
story.append(Paragraph("(Autonomous Institution)", S["center"]))
story.append(Paragraph("<b>COIMBATORE \u2013 641 004</b>", S["center"]))
story.append(PageBreak())

# ================================================================ BONAFIDE
story.append(Paragraph("<b>PSG COLLEGE OF TECHNOLOGY</b><br/>(Autonomous Institution)<br/><b>COIMBATORE \u2013 641 004</b>", S["center"]))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(f"<b>{TITLE}</b>", ParagraphStyle("b1", alignment=TA_CENTER, **dict(base, fontSize=14, leading=20))))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Bona fide record of work done by", S["center"]))
story.append(Spacer(1, 0.3 * cm))
t = Table([[n, f"(Roll No: {r})"] for n, r in TEAM], colWidths=[5.2 * cm, 4.0 * cm])
t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Times", 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
story.append(t)
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph("Dissertation submitted in partial fulfillment of the requirements for the degree of<br/><b>BACHELOR OF ENGINEERING</b><br/>Branch : COMPUTER SCIENCE and ENGINEERING<br/>of Anna University<br/>" + DATE, S["center"]))
story.append(Spacer(1, 0.9 * cm))
sig = Table([["...................................", "...................................."],
             [GUIDE, "Dr. G. R. Karpagam"], ["Faculty guide", "Head of the Department"],
             [COGUIDE, ""], ["Co-guide", ""]], colWidths=[7.8 * cm, 7.8 * cm])
sig.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Times", 12), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
story.append(sig)
story.append(Spacer(1, 0.8 * cm))
story.append(Paragraph("Certified that the candidates were examined in the viva-voce examination held on ..................", S["bodyni"]))
story.append(Spacer(1, 0.7 * cm))
ex = Table([["......................................", "......................................"],
            ["(Internal Examiner)", "(External Examiner)"]], colWidths=[7.8 * cm, 7.8 * cm])
ex.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Times", 12), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
story.append(ex)
story.append(PageBreak())

# ================================================================ CERTIFICATE
story.append(Paragraph("CERTIFICATE", S["front"]))
names = ", ".join(f"{n} ({r})" for n, r in TEAM[:-1]) + f", {TEAM[-1][0]} ({TEAM[-1][1]})"
story.append(Paragraph(
    f"Certified that this report titled \u201c{TITLE}\u201d for the Project work I (23Z711) is a bonafide work of {names} "
    "who have carried out the work under my supervision for the partial fulfillment of the requirements for the award of the "
    "degree of Bachelor of Engineering in Computer Science and Engineering. Certified further that to the best of my knowledge "
    "and belief, the work reported herein does not form part of any other thesis or dissertation based on which a degree or an "
    "award was conferred on an earlier occasion.", ParagraphStyle("cert", alignment=TA_JUSTIFY, firstLineIndent=1 * cm, **dict(base, leading=22))))
story.append(Spacer(1, 0.8 * cm))
story.append(Paragraph("Place : Coimbatore<br/>Date :", S["bodyni"]))
story.append(Spacer(1, 0.8 * cm))
story.append(Paragraph(f"<b>Faculty guide :</b><br/>{GUIDE}<br/>Department of Computer Science and Engineering,<br/>PSG College of Technology<br/>Coimbatore-641004", S["bodyni"]))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph(f"<b>Co-guide :</b><br/>{COGUIDE}<br/>Department of Computer Science and Engineering,<br/>PSG College of Technology<br/>Coimbatore-641004", S["bodyni"]))
story.append(Spacer(1, 0.6 * cm))
story.append(Paragraph("<b>COUNTERSIGNED</b><br/><br/><br/><b>HEAD</b><br/>Department of Computer Science and Engineering,<br/>PSG College of Technology,<br/>Coimbatore-641004", S["bodyni"]))
story.append(PageBreak())

# ================================================================ CONTENTS
story.append(Paragraph("CONTENTS", S["front"]))
toc = TableOfContents(dotsMinLevel=0)
toc.levelStyles = [
    ParagraphStyle("t0", fontName="Times-B", fontSize=11.5, leading=15.5, leftIndent=0, firstLineIndent=0, spaceBefore=3),
    ParagraphStyle("t1", fontName="Times", fontSize=10.5, leading=13.5, leftIndent=1.0 * cm, firstLineIndent=0),
]
story.append(toc)
story.append(NextPageTemplate("front"))
story.append(PageBreak())

# ================================================================ ACKNOWLEDGEMENT
story.append(Paragraph("ACKNOWLEDGEMENT", S["front"]))
for t in [
    "We would like to extend our sincere thanks to our Principal (FAC - In Charge), Dr. G. Thilagavathi, for providing us with the opportunity "
    "to develop and complete our project in our field of interest.",
    "We express our sincere thanks to our respectful Head of the Department, Dr. G. R. Karpagam, for encouraging and "
    "allowing us to work on and present the project at our department for the partial fulfillment of the requirements leading to the "
    "award of the B.E. degree.",
    f"We take immense pleasure in conveying our thanks and a deep sense of gratitude to our faculty guide, {GUIDE}, Department of "
    f"Computer Science and Engineering, and our co-guide, {COGUIDE}, for their relentless support, encouragement and suggestions, "
    "and for pushing us to test every claim against evidence rather than assumption throughout this project.",
    "We also thank the authors of the open-source tools and public datasets on which this work stands: the PyBullet and "
    "gym-pybullet-drones simulators, the Ultralytics YOLO framework, and the MBDD2025 building-defect dataset. Finally, we thank "
    "our families and friends for their patience and support during the long experiment runs that this project required.",
]:
    story.append(Paragraph(t, ParagraphStyle("ack", alignment=TA_JUSTIFY, firstLineIndent=1 * cm, **dict(base, leading=22, spaceAfter=10))))
story.append(PageBreak())

# ================================================================ SYNOPSIS
UWp, UWr, UWf = M("uwtig", "precision_confirmed"), M("uwtig", "recall_confirmed"), M("uwtig", "f1_confirmed")
RKf, RKfly, UWfly = M("ruckin_ipp", "f1_confirmed"), M("ruckin_ipp", "total_flight_dist_m"), M("uwtig", "total_flight_dist_m")
FLYLESS = round(100 * (1 - UWfly / RKfly))
story.append(Paragraph("SYNOPSIS", S["front"]))
for t in [
    "Inspecting buildings, towers and pipelines for cracks, corrosion and leakage is repetitive work, and the autonomy that "
    "robots bring to it is usually limited to flying a fixed route or maximising how much surface is seen. Existing next-best-view "
    "planners decide where to look using geometry alone: they have no idea what a defect is, they forget everything between "
    "flights, and they never treat an unsure detection as a reason to look again. This project designs a planner that does.",
    "Our contribution is <b>UW-TIG (Uncertainty-Weighted Temporal Information Gain)</b>. It keeps the cost-normalised information-gain "
    "formulation common to recent uncertainty-driven planners (R\u00fcckin et al., 2023; Moon et al., 2026) and adds a coverage guarantee, detection uncertainty from a trained YOLO detector, "
    "persistent cross-mission defect memory with growth tracking, a persistent-monitoring staleness term, and a two-step "
    "receding-horizon lookahead. Because a physical drone and a real defective structure are not needed to show or measure this, "
    "the second major contribution is a <b>reproducible simulation testbed</b>: an open-air utility yard in PyBullet textured "
    "with real photographs from the MBDD2025 dataset, a 54-viewpoint candidate graph (9 walls) that scales to a 186-viewpoint graph over 31 walls, four defect scenarios, a fast kinematic mode "
    "for statistics and a PID-flight mode for demonstration, and an evaluation harness with separate development and test seeds.",
    f"On held-out test seeds the original nine-wall yard gives UW-TIG a precision of {f3(UWp)}, a recall of {f3(UWr)} and an F1 of {f3(UWf)}, compared "
    f"with five re-implemented published planners; it ties the strongest of them on detection quality (F1 {f3(RKf)}) while flying "
    f"{FLYLESS}% less. To test whether this survives scale, the yard was enlarged to 31 inspectable walls and every planner re-run: "
    f"UW-TIG reaches an F1 of {f3(SP('large_old', 'uwtig', 'f1_confirmed'))} there, statistically level with the best classical rule and ahead of "
    f"R\u00fcckin\u2019s IPP, with fewer metres flown than IPP. The detector was also fine-tuned on two further public datasets (dacl10k and a "
    f"Roboflow corrosion set): its score on held-out dacl10k images rose from {DET['old']['dacl']['map50']:.3f} to {DET['new']['dacl']['map50']:.3f} mAP50 "
    f"without changing its MBDD2025 score, but it did not improve the closed loop, so the original detector remains the default. The report also documents what did not work, "
    "what was wrong with our own measurements, and the limitations that remain.",
    "limitations that remain.",
]:
    story.append(Paragraph(t, ParagraphStyle("syn", alignment=TA_JUSTIFY, firstLineIndent=1 * cm, **dict(base, leading=20, spaceAfter=9))))
story.append(PageBreak())

# ================================================================ LISTS
story.append(Paragraph("LIST OF FIGURES", S["front"]))
figs = FigList("FigEntry", dotsMinLevel=0)
figs.levelStyles = [ParagraphStyle("f0", fontName="Times", fontSize=10.5, leading=14, leftIndent=0)]
story.append(figs)
story.append(PageBreak())
story.append(Paragraph("LIST OF TABLES", S["front"]))
tabs = FigList("TabEntry", dotsMinLevel=0)
tabs.levelStyles = [ParagraphStyle("f1", fontName="Times", fontSize=10.5, leading=14, leftIndent=0)]
story.append(tabs)
story.append(NextPageTemplate("body"))

# ================================================================ 1 INTRODUCTION
H1(1, "Introduction", "Introduction")
P("Utility infrastructure \u2013 building facades, bridges, pipelines, transmission towers \u2013 degrades continuously. Cracks "
  "widen, corrosion spreads and leakage stains grow, and the only way to know is to look, repeatedly, over months and years. "
  "Unmanned aerial vehicles have made looking cheaper and safer, and deep-learning detectors can now find defects in the "
  "photographs they bring back. What has advanced much more slowly is the part in between: the decision of <i>where the "
  "vehicle should look next</i>.")
P("In most deployed systems that decision is made before take-off. A route is planned, the drone flies it, and the images are "
  "analysed afterwards. Detection confidence never changes the route, a defect found last month is not remembered this month, and "
  "a blurry, low-confidence detection is either trusted or discarded rather than <i>checked</i>. Research on next-best-view (NBV) "
  "planning does close the loop between what has been seen and where to go, but it optimises coverage of geometry: the planner "
  "is rewarded for revealing unseen surface, whether or not that surface holds anything of interest.")
P("This project asks a simple question: <b>what changes if the planner knows what a defect is, knows how sure the detector is, "
  "and remembers what it saw last time?</b> Answering it properly needs two things that are rarely built together \u2013 a planner "
  "with those three abilities, and an experimental environment in which the planner can be compared fairly against published "
  "alternatives, many times, with ground truth. This report is about both.")
H2("1.1. Objective")
P("The objectives of the project are:")
B(["To design a planner, UW-TIG, that selects inspection viewpoints using detector uncertainty, defect growth recorded in "
   "persistent memory, revisit staleness and a short lookahead, in addition to the geometric information gain used by the "
   "planners of recent work (R\u00fcckin et al., 2023).",
   "To build a simulation testbed in which this planner and several published planners can be run on identical scenes, "
   "detectors, seeds and scoring, and in which the defect appearance is real (photographs), not synthetic.",
   "To measure the planner honestly: choose every parameter on development seeds, report once on separate test seeds, "
   "include ablations of every added mechanism, and report failures alongside successes."])
H2("1.2. Overview")
P("The system is a closed loop with five stages (Chapter 4). A <b>planner</b> chooses one of 54 candidate viewpoints. A "
  "<b>simulated camera</b> renders what the drone would see from there. A trained <b>YOLO detector</b> reports defects with a "
  "confidence and an uncertainty (the spread of its confidence over five photometrically perturbed copies of the frame). Each "
  "detection is <b>ray-cast</b> from the camera onto the known wall plane to obtain a 3-D position and a physical size. A "
  "<b>persistent memory</b> (PostgreSQL with pgvector, and Neo4j) matches the detection to a defect it has seen before, or "
  "registers a new one, and records how much the defect has grown. The updated uncertainty and growth feed back into the "
  "planner\u2019s next decision, and are re-loaded at the start of the next mission.")
P("The simulation is as much a part of the contribution as the planner. It consists of an open-air utility yard with nine "
  "inspectable surfaces whose textures are cropped from real MBDD2025 photographs, a candidate-viewpoint graph with two "
  "standoff distances chosen from a detector diagnostic, four scenarios (static, uncertain, growing, multiple defects), and an "
  "evaluation protocol with a development/test split. Because the simulation is cheap, the planner comparison could be run over "
  "5 test seeds \u00d7 4 scenarios \u00d7 12 planners \u00d7 3 missions \u2013 an experiment that would be impractical with a physical "
  "drone and that is, in any case, impossible to repeat identically in the field.")
H2("1.3. Scope")
P("<b>In scope:</b> the UW-TIG planner and its ablations; re-implementations (at the level of the viewpoint-selection rule) of "
  "four published planners; the PyBullet testbed; a YOLO detector trained on a public dataset; the memory and geometry "
  "components that connect them; and a quantitative comparison with a statistical protocol.")
P("<b>Out of scope:</b> hardware flight; obstacle avoidance and dynamics beyond a PID-controlled quadrotor model; "
  "photo-realistic rendering (Section 4.12 explains why this is a deliberate choice); and the authors\u2019 full original systems "
  "for the compared papers. These boundaries are repeated, with their consequences, in Chapters 6 and 7.")

# ================================================================ 2 LITERATURE SURVEY
H1(2, "Literature Survey", "Literature Survey")
H2("2.1. Literature Survey")
H3("2.1.1. Uncertainty-aware informative path planning (2023 \u2013 2026)")
P("R\u00fcckin et al. [1] plan UAV paths for active learning in semantic mapping, using a model\u2019s own epistemic uncertainty (MC-Dropout) "
  "to decide where to look, normalised by travel cost. The structure is the closest to UW-TIG\u2019s utility, but the uncertainty is spent to "
  "<i>improve the model</i> within one session, not to monitor a fixed defect set across sessions. Vashisth et al. [2] learn adaptive "
  "informative path planning with deep reinforcement learning on dynamic graphs; Moon et al. (IA-TIGRIS) [3] present a sampling-based "
  "planner that reuses earlier planning effort and adapts to updated belief maps, evaluated on multirotor and fixed-wing UAVs; "
  "Li et al. [4] select views under motion and measurement uncertainty for reconstructing moving objects. These works show the "
  "field moving toward learned and adaptive planners, but all of them reason about information gain over a generic belief, not "
  "about defects with an identity and a history.")
H3("2.1.2. Inspection-specific planning (2023 \u2013 2025)")
P("Dhami et al. introduced GATSBI [8, 9], an online algorithm that routes a UAV over target surfaces of a bridge with a "
  "generalised travelling-salesman formulation; the 2024 extension adds a defect detector. It is the closest published system "
  "to inspection-aware planning, but it plans within a single session and has neither a detection-uncertainty term nor memory "
  "across sessions. Pred-NBV and MAP-NBV [10] use a learned shape-completion model to guide views, an indirect form of "
  "uncertainty about geometry rather than about defects.")
P("Petit and Lussier Desbiens [5] (MOAR) plan risk-aware, multi-objective paths for infrastructure inspection that adapt to "
  "weather and battery state; Svystun et al. [6] adapt trajectories to the pitch of wind-turbine blades using segmentation, "
  "reporting a 78% reduction in inspection time; Jin et al. [7], extended as ASIP-Planner (IROS 2026) [26], combine global coverage planning with local reactive "
  "re-planning for surface inspection in partially unknown indoor environments; FC-Vision [27] (RA-L 2026) repairs viewpoints in real time when unexpected obstacles occlude a scan. None of these plans around detected defects, and "
  "none revisits a defect across missions. Two 2025 reviews [11, 12] of decision-making UAV path planning and of UAV infrastructure "
  "inspection both identify perception-driven flight planning, and fusion of detection with planning, as an open problem.")
H3("2.1.3. Classical building blocks")
P("The recent planners above rest on older ideas, three of which UW-TIG also uses as ingredients. Isler et al. [23] formulate "
  "next-best-view selection as maximising an entropy-based information gain, normalised by travel cost; Bircher et al. [24] plan over "
  "a tree of motions and execute only the first step (a receding horizon); Alamdari, Fata and Smith [25] minimise the maximum latency "
  "between observations for persistent monitoring. We re-implement these three selection rules as baselines so that the comparison "
  "spans both generations of planner, but they are not the reference point of this work: they have no notion of a defect, "
  "and the contribution is measured primarily against the recent, perception-aware planners of Sections 2.1.1 and 2.1.2.")
H3("2.1.4. Defect detection and datasets")
P("Zha et al. [13] publish MBDD2025, 14,471 UAV photographs of building surfaces in six structure types and five defect classes "
  "(crack, leakage, abscission, corrosion, bulge), with bounding-box annotations and a benchmark of 35 detectors; it is the dataset "
  "used here. Recent detectors report high scores on narrower problems: Huang et al. [14] reach 0.913 precision, 0.766 recall and "
  "0.864 mAP@50 for concrete cracks with an improved YOLOv11; Inam et al. [15] report 0.977 / 0.967 / 0.993 for bridge cracks "
  "(one class); Li, Shi and Sun [16] report 0.932 / 0.924 / 0.926 on a private 5,000-image utility-tunnel dataset. Shen et al. "
  "[17] propose TinyDef-DETR, a transformer detector for transmission-line defects, and Hebbache et al. [18] a saliency-guided "
  "YOLOX detector for bridge defects. These results are not directly comparable to a five-class public benchmark, a point "
  "Chapter 6 returns to. For bridges, Flotzinger et al. [28] released dacl10k (9,920 inspection photographs, 19 classes, segmentation-first), and "
  "its 2025 follow-up [29] shows that rebalancing it with synthetic crack and cavity textures improves segmentation robustness by about two points; "
  "Roboflow-100 [30] is a public multi-domain detection benchmark from which a corrosion set is taken here; and \u00d6zgenel and Sorgu\u00e7 [31] and "
  "Dorafshan et al. [32] (SDNET2018) are the standard concrete-crack image collections.")
H3("2.1.5. Simulation platforms")
P("AirSim [19] builds on Unreal Engine for high-fidelity rendering and physics; Flightmare [20] couples a Unity renderer with "
  "a separate fast physics engine; GRaD-Nav [21] represents the frontier with 3-D Gaussian Splatting. All three address the gap "
  "between rendered and real imagery when a model is <i>trained</i> on synthetic images. gym-pybullet-drones [22] provides "
  "a PyBullet quadrotor with PID control and an onboard camera, and is the physics layer used here.")
TABLE("2.1", "Summary of the reviewed planning literature", ["Paper, authors and year", "Technique", "Advantages", "Limitations"], [
    ["R\u00fcckin et al., T-RO 2023 [1]", "MC-Dropout uncertainty drives path", "Real model uncertainty in planning", "Single session; goal is retraining"],
    ["Dhami et al. (GATSBI), 2023/24 [8,9]", "GTSP routing + detector", "Inspection-aware, cost-aware", "Single session; no uncertainty/memory"],
    ["Vashisth et al., 2024 [2]", "Deep RL on dynamic graphs", "Learned, adaptive", "Needs training; no defect history"],
    ["Petit & Lussier Desbiens, ICRA 2024 [5]", "Risk-aware multi-objective planning", "Weather/battery adaptive", "No perception or defects"],
    ["Svystun et al., 2024 [6]", "Segmentation-guided trajectories", "78% shorter inspection", "One structure type; no revisits"],
    ["Jin et al., 2025 [7]", "Global coverage + local replanning", "Handles unmapped obstacles", "Coverage only"],
    ["Moon et al., T-RO 2026 [3]", "Incremental sampling-based IPP", "Fast online replanning", "Generic gain; no defects"],
    ["Li et al., RSS 2026 [4]", "NBV under motion uncertainty", "Plans over uncertain futures", "Reconstruction, not inspection"],
    ["Isler / Bircher, ICRA 2016 [23,24]", "Entropy-gain NBV; receding horizon", "Classical building blocks (baselines)", "Geometry only; no defects, no memory"],
    ["Alamdari et al., IJRR 2014 [25]", "Max-latency revisit scheduling", "Guaranteed regular revisits", "Time only; no perception"],
], [4.6 * cm, 3.9 * cm, 3.4 * cm, 3.7 * cm], left=(0, 1, 2, 3))
H2("2.2. Inference")
P("Three patterns emerge from the survey. First, <b>planning has become more capable but not more defect-aware</b>: 2023\u20132026 "
  "planners add learning, risk-awareness and incremental re-planning, yet their objective remains coverage or information gain "
  "over a generic belief. Second, <b>uncertainty-driven planning exists but is spent inside a single session</b> and aimed at "
  "improving a model, not at monitoring defects. Third, <b>persistence exists only as a revisit schedule</b>: Alamdari et al. know "
  "<i>when</i> to return, but nothing in the reviewed planners decides to return because of <i>what was seen</i>, such as a "
  "detection that was unsure or a defect that was growing.")
P("On the detection side, the strongest published numbers come from single-class or private data, and the planning "
  "literature almost never evaluates against a real trained detector, relying instead on assumed ground-truth detections. A "
  "planner evaluated against a real detector inherits its failure modes \u2013 low recall at short range, false positives from "
  "neighbouring surfaces, poor calibration \u2013 and these turned out to matter greatly in this project (Chapters 5 and 6).")
H2("2.3. Research Gap")
P("No reviewed work combines, in one planner that is evaluated against a real trained detector: (i) detection uncertainty as a "
  "reason to revisit; (ii) defect identity and growth remembered across missions; (iii) revisit staleness; and (iv) a "
  "cost-aware, short-horizon decision rule. Moreover, no reviewed work provides a controlled testbed in which such a planner can "
  "be compared with several published planners under identical conditions, with real defect imagery and a development/test split.")
H2("2.4. Research Objectives")
B(["Introduce UW-TIG, a planner whose utility combines coverage information gain, detector uncertainty, defect growth, staleness "
   "and cost, selected with a two-step lookahead, preceded by an explicit coverage guarantee.",
   "Build a simulation testbed with real defect imagery, a fixed viewpoint graph, four scenarios and a leakage-free memory, so "
   "that every planner is measured on exactly the same inputs.",
   "Re-implement the selection rules of four published planners and compare them with UW-TIG and with random search.",
   "Ablate every added mechanism and report which ones measurably help, which do not, and why.",
   "Report limitations, including the calibration of the uncertainty signal and the failure of the growing-defect scenario."])

# ================================================================ 3 SYSTEM REQUIREMENTS
H1(3, "System Requirements", "System Requirements")
H2("3.1. Hardware Requirements")
B(["<b>Development machine:</b> Windows 11 workstation, multi-core x86-64 processor (sweeps run several seeds in parallel).",
   "<b>Memory:</b> enough for several parallel seed processes, each holding a PyBullet client, a YOLO model and the detection memory.",
   "<b>Storage:</b> several GB for the dataset (MBDD2025, 14,471 images and labels), model weights, results and logs.",
   "<b>GPU:</b> one NVIDIA L4 (24 GB) on a rented 32-vCPU machine, used for the 100-epoch YOLOv8s training, a later YOLO11m "
   "retrain, the fine-tuning on merged datasets, and the parallel planner sweeps of the 31-wall yard. The original nine-wall sweep ran on the Windows workstation."])
H2("3.2. Software Requirements")
TABLE("3.1", "Software stack", ["Component", "Tool / version", "Purpose"], [
    ["Language", "Python 3.12", "All simulation, planning, perception and analysis code"],
    ["Physics and rendering", "PyBullet; gym-pybullet-drones", "Quadrotor with PID control (DSLPIDControl), onboard camera, TinyRenderer"],
    ["Detection", "Ultralytics YOLOv8 / YOLO11; OpenCV; NumPy", "Defect detector, test-time augmentation, image resampling"],
    ["Persistent memory", "PostgreSQL + pgvector; Neo4j", "Detection log, appearance/spatial matching; defect identity graph"],
    ["Deployment", "Docker Compose", "Runs both databases locally"],
    ["Textures", "Pillow", "Wall, ground and sky texture generation and cropping"],
    ["Analysis and reporting", "matplotlib; ReportLab; pptxgenjs", "Charts, this report, the review deck"],
    ["Version control", "Git / GitHub", "Reproducibility of every reported number"],
], [3.5 * cm, 5.4 * cm, 6.7 * cm], left=(0, 1, 2))

H2("3.3. Datasets")
P("Four public datasets are used, each for a different purpose; a fifth, SDNET2018, was planned but could not be obtained. "
  "Table 3.2 lists them. MBDD2025 provides both the detector\u2019s training data and, as wall textures, the defect appearance in the "
  "simulation. The two further datasets were added to test whether a broader training set improves the detector, and the "
  "concrete-crack crops provide an image-level check on data never trained on.")
TABLE("3.2", "Datasets used", ["Dataset", "Content", "Use here", "Size used"], [
    ["MBDD2025 [13]", "UAV photographs of building surfaces; 5 classes (crack, leakage, abscission, corrosion, bulge); boxes", "Detector training, validation and test; wall textures", "10,129 / 2,894 / 1,448 images (train / val / test); training adds 2,826 bulge duplicates"],
    ["dacl10k [28]", "Real bridge-inspection photographs; 19 classes with polygon and box labels (CC-BY-4.0)", "Fine-tuning (train split); held-out cross-dataset test (validation split)", "5,362 train + 466 val; 810 held out"],
    ["Roboflow-100 corrosion [30]", "Corrosion and crack boxes (CC-BY-4.0)", "Fine-tuning", "851 images"],
    ["Concrete cracks (\u00d6zgenel) [31]", "227 \u00d7 227 crops, cracked or not (CC-BY-4.0)", "Image-level crack-presence check; never trained on", "400 cracked + 400 uncracked"],
    ["SDNET2018 [32]", "56,000 concrete crack / no-crack crops", "Planned; download blocked by a bot check on every mirror we reached", "not used"],
], [2.8 * cm, 4.9 * cm, 4.4 * cm, 3.6 * cm], left=(0, 1, 2, 3))
P("<b>Class mapping.</b> dacl10k has 19 classes, MBDD2025 five. Crack and alligator crack map to <i>crack</i>; wet spot and efflorescence "
  "to <i>leakage</i>; spalling and rock pocket to <i>abscission</i>; rust and exposed rebar to <i>corrosion</i>. dacl10k has no counterpart of "
  "<i>bulge</i>, and its other classes are ignored. The mapping is a judgement, not a given: efflorescence in particular is a "
  "water-related deposit rather than a leak, so the leakage labels are noisier than the others. The Roboflow set maps corrosion and "
  "crack directly and drops its \u201cSlippage\u201d class. dacl10k boxes come from the dataset\u2019s own detection layer; its polygon "
  "masks were not used.")
P("<b>Held-out discipline.</b> MBDD2025\u2019s split is unchanged, so the MBDD test score remains comparable with every earlier result. "
  "dacl10k\u2019s own validation split is never used for training or early stopping; 8% of its training split is held back for "
  "validation instead.")

# ================================================================ 4 SYSTEM DESIGN
H1(4, "System Design", "System Design")
H2("4.1. Overall Architecture")
P("Fig. 4.1 shows the closed loop. The planner, the simulated drone and camera, the detector, the geometry module and the "
  "persistent memory form a cycle; the feedback from memory to planner is what distinguishes this system from a pipeline that runs "
  "once. The same loop runs in two modes (Section 4.3): a fast kinematic mode used for the statistics and a PID-flight mode used "
  "for demonstration.")
FIG(os.path.join(HERE, "architecture_diagram.png"), 14.2 * cm, "4.1", "System architecture: the five-stage closed loop")
H2("4.2. Simulation Environment")
P("The environment is an <b>open-air utility yard</b> (Fig. 4.2). It replaced an earlier enclosed two-room house: in an enclosed "
  "building the drone never sees anything but walls, the sky is a white void, and the scene reads as a house tour rather than "
  "infrastructure. The yard has two freestanding buildings \u2013 Building A (four walls, 4 m \u00d7 4 m) and Building B (three walls, "
  "2.6 m \u00d7 2.6 m) \u2013 about 11 m apart with open sky between them, and one inspection panel each on a decorative pipe rack "
  "and a lattice tower. In total there are <b>nine inspectable surfaces</b>. A sky backdrop with a skyline silhouette, a "
  "procedurally generated concrete ground texture and small props (crates, barrels) dress the scene.")
FIG(os.path.join(FIGS, "yard_plan.png"), 14.2 * cm, "4.2", "Plan view of the yard: nine inspectable surfaces and the 54 candidate viewpoints")
FIG(os.path.join(HERE, "establishing_shot.png"), 8.6 * cm, "4.3", "Establishing shot of the simulated yard rendered with PyBullet")
H3("4.2.0. Two layouts: nine walls and thirty-one")
P("Every result up to Section 6.7 was produced in the nine-wall yard described above. A fair objection is that nine walls and a 16-step "
  "budget are an easy problem: a planner that visits every wall once has nearly solved it. The yard was therefore enlarged "
  "(selected with the environment variable UWTIG_YARD=large) to <b>31 inspectable surfaces</b>: four more equipment buildings "
  "(C 4 m \u00d7 4 m, D and E 3.2 m \u00d7 3.2 m, F 2.6 m \u00d7 2.6 m) and six more freestanding inspection panels, spread over roughly "
  "34 m \u00d7 28 m. The candidate graph grows from 54 to <b>186 viewpoints</b> (six per wall) and the mission budget from 16 to 50 "
  "steps, keeping the ratio of budget to walls near 1.7. Fig. 4.4 shows the layout.")
FIG(os.path.join(FIGS, "yard_large.png"), 14.2 * cm, "4.4", "Plan view of the 31-wall yard (buildings A\u2013F, the pipe rack, the tower and six panels) and its 186 viewpoints")
H3("4.2.1. Walls as textured quads")
P("Every inspectable surface is a flat quadrilateral mesh with a texture bound to it. A wall is defined by its centre, its yaw "
  "and its width; the plane it lies on, its outward normal and its in-plane axes follow from these (geometry.wall_plane). Using "
  "flat quads rather than boxes keeps the geometry of every wall analytically known, which is what makes ray-casting a "
  "detection back onto the wall exact (Section 4.7).")
H3("4.2.2. Real defect imagery as wall texture")
P("A wall\u2019s defect is a real photograph from MBDD2025 applied as its texture. For a defect scenario, a photograph containing the "
  "wanted class is selected and a region is <b>cropped to the wall\u2019s true aspect ratio</b> (width divided by the 2.4 m wall height) "
  "at a long side of 1536 pixels. This crop was not in the first design: the early textures were square images stretched over walls "
  "up to 4 m wide, which distorted defects by roughly 2.2\u00d7 and left them pixelated, so the detector was being tested on imagery "
  "it had never been trained for. Ground-truth defect centres are kept in a fixed 512-unit texture space so that the same physical "
  "spot is reproduced from mission to mission and can be converted to a world position analytically (texture_uv_to_world).")
P("Real photographs also contain defects of other classes: about 16% of MBDD2025 photos carry a second labelled defect. The "
  "scenario therefore records <i>which classes are present</i> in the cropped region, so that detecting a second real defect is not "
  "scored as a false positive (Section 4.10).")
H3("4.2.3. Camera and rendering")
P("The onboard camera follows the gym-pybullet-drones convention: a 60\u00b0 field of view rendered into a 320 \u00d7 240 frame with the "
  "projection matrix built for an aspect ratio of 1.0. The frame is therefore stretched horizontally by 4/3 relative to a "
  "square-pixel image. Because the detector was trained on undistorted photographs, every frame is resampled to square pixels "
  "before inference and the detected boxes are mapped back, so that localisation still uses the original geometry (Section 4.6).")
P("Rendering uses PyBullet\u2019s TinyRenderer, a software rasteriser with shadow mapping. It is not a physically based renderer; "
  "the realism work in this project was limited to what changes the <i>detector\u2019s</i> input: consistent light direction and "
  "shadows, higher-resolution ground and sky textures, and a fix for a texture-tiling bug in box geometry (Section 5.2).")
H2("4.3. Two Simulation Modes")
P("Detection and planning quality do not depend on rotor dynamics, so the statistical comparison does not need to step a "
  "physics engine for every flight. The testbed therefore has two modes that share the same scene, the same camera convention and "
  "the same planner code:")
B(["<b>Kinematic mode</b> (experiments/kinematic_capture.py): the virtual camera is teleported to a candidate viewpoint and "
   "rendered. No PID stepping is performed. This mode runs the planner comparison.",
   "<b>PID-flight mode</b> (demo_uwtig_flight.py): a gym-pybullet-drones quadrotor flies between viewpoints under DSLPIDControl, "
   "with a smoothstep (ease-in, ease-out) reference to avoid velocity discontinuities, and a smoothed chase camera. This mode "
   "produces the demonstration videos."])
P("The two modes use the same localisation mathematics, so what is verified in one carries to the other. The demonstration "
  "script accepts any planner by name, which allows the same scenario, seed and budget to be flown by different planners and "
  "the videos placed side by side \u2013 a way of <i>showing</i> the difference without any physical drone.")
H2("4.4. Candidate Viewpoint Graph")
P("For each wall, the viewpoint generator creates stations at two <b>standoff distances</b>, 1.3 m and 2.2 m, and three lateral "
  "offsets (\u22120.55, 0 and +0.55 of the half-width), giving 54 viewpoints in all. Each viewpoint stores its pose and the "
  "<b>cells</b> of its wall that it can see. Surface coverage is discretised into cells of a fixed physical width of 1 m, so a 4 m "
  "wall has four cells and a 1.2 m panel one. This choice, following the fixed voxel <i>size</i> of classical volumetric planners [23], fixed a "
  "failure found early: with a fixed number of cells per wall, a narrow wall\u2019s single viewpoint saw all of its surface at once, "
  "earned a disproportionate information gain, and the planner froze on the small panels for an entire mission.")
P("The 2.2 m standoff was added after a detection diagnostic on development seeds (Section 6.2). The cost of moving between "
  "viewpoints is the Euclidean distance plus a very small rotation term (1/3600 m per degree of yaw), whose only job is to break "
  "ties between viewpoints at exactly the same position, which occur in Building B because its 2.6 m width is exactly twice the "
  "1.3 m standoff.")
H2("4.5. Scenarios")
TABLE("4.1", "The four defect scenarios", ["Scenario", "Defects", "Severity", "Purpose"], [
    ["Static", "A-west crack, A-east corrosion, B-north leakage (MBDD2025 photos)", "1.0 (fixed)", "Steady-state detection and coverage"],
    ["Uncertain", "A-south crack, B-east corrosion (MBDD2025 photos)", "0.35 (faint)", "Low-confidence, ambiguous defects"],
    ["Multi-defect", "Six walls, three classes (MBDD2025 photos)", "0.9", "Coverage breadth vs. reinspection depth"],
    ["Growing", "A-east corrosion, procedurally generated", "0.4 to 1.3 over missions", "Known-growth ground truth for the memory"],
], [2.6 * cm, 6.4 * cm, 2.9 * cm, 3.7 * cm], left=(0, 1, 3))
P("Three scenarios use real photographs. The fourth, <i>growing</i>, needs a defect whose true size changes by a known amount "
  "between missions; no single-time-point photograph dataset can provide that, so it uses a procedural texture. This is the one "
  "scenario where the detector fails, for a reason documented in Section 6.7. In the 31-wall yard the defect walls are not a fixed list: "
  "each scenario draws its walls without replacement from all 31 by a random generator seeded with the scenario and seed "
  "(8 walls for static, 6 for uncertain, 2 for growing, 16 for multi-defect, classes cycled), so defect placement varies from seed to seed.")
H2("4.6. Perception")
P("The detector is a YOLOv8s model at 640 px trained on MBDD2025 with a 70/20/10 split (Section 6.1). For each frame the system "
  "builds five inputs: the square-pixel frame and four photometric variants (brightness/contrast, additive noise, blur, and a "
  "blurred, re-brightened copy) that move no pixel geometry. The model runs on all five. For every detection in the original frame, "
  "the confidence of the best-overlapping same-class box in each variant (zero if there is none) is collected, and the "
  "<b>standard deviation</b> across the five is reported as the detection\u2019s <b>uncertainty</b>. This test-time-augmentation "
  "ensemble is a substitute for MC-Dropout; Section 6.6 and Chapter 7 discuss why a literal MC-Dropout was not adopted.")
H2("4.7. 3-D Localisation")
P("A detection\u2019s centre pixel is turned into a ray using the camera\u2019s view and projection matrices and intersected with "
  "the plane of the wall being inspected. A hit is accepted only if it lies <b>inside the wall\u2019s physical rectangle</b> (with a "
  "5 cm margin). The rectangle test matters: a ray through a pixel that shows an adjacent wall, the ground or a prop still "
  "intersects the inspected wall\u2019s <i>infinite plane</i> somewhere, so without the test the defect was attributed to the wrong "
  "surface. On development seeds this accounted for 51\u201375% of all false positives, against one of 1,369 true positives. The "
  "box\u2019s two corners are localised the same way (without the rectangle test) to give a physical size in metres, used for growth.")
H2("4.8. Persistent Defect Memory")
P("Memory has two stores. <b>PostgreSQL with pgvector</b> holds an append-only log of every detection and uses the stored "
  "appearance embedding of the cropped detection and its world position to match a new detection to an existing defect. "
  "<b>Neo4j</b> holds the defect graph: defect nodes linked to the missions that observed them and the walls they lie on. When a "
  "detection matches a known defect, its <i>growth</i> is the difference between its current and previous physical size; "
  "otherwise a new defect is registered. At the start of every mission after the first, the planner\u2019s belief is seeded with "
  "each active defect\u2019s last uncertainty and its growth. Memory keys are namespaced per scenario, planner and seed, so that no "
  "planner can see another\u2019s detections (Section 5.4). The 31-wall sweeps ran on a rented machine without Docker, so a second, "
  "in-process implementation of the same store was written (memory/store_mem.py). It ports the matching rule exactly \u2013 among the five "
  "nearest detections of the same class on the same wall by cosine distance of the embedding, the nearest one within 0.35 m is the same defect \u2013 "
  "but does not mirror the Neo4j graph, which no planner or metric reads. The two implementations were not run against each other on the "
  "same sweep, so this is a faithful port, not a verified equivalent.")
H2("4.9. The UW-TIG Planner")
P("This section is the core of the contribution. The planner chooses the next viewpoint <i>v</i> from the 54 candidates. Its design "
  "has one front-end rule and one utility.")
FIG(os.path.join(FIGS, "planner_flow.png"), 13.0 * cm, "4.5", "UW-TIG decision flow for one step")
H3("4.9.1. The utility")
PN("<b>U(v) = w<sub>ig</sub>\u00b7IG(v) + w<sub>u</sub>\u00b7Unc(v) + w<sub>g</sub>\u00b7Growth(v) + w<sub>s</sub>\u00b7Stale(v) \u2212 w<sub>c</sub>\u00b7Cost(v)</b>")
PN("with w<sub>ig</sub> = 1.0, w<sub>u</sub> = 1.5, w<sub>g</sub> = 2.0, w<sub>s</sub> = 1.0 and w<sub>c</sub> = 0.4. The terms are as follows.")
B(["<b>Information gain IG(v)</b> (the cost-normalised entropy term of [23], shared by the planners of Chapter 2). Each cell has a belief <i>p</i> = 1 \u2212 0.5\u00b7e<super>\u22120.6\u00b7n</super> that "
   "it is already adequately observed after <i>n</i> views; its entropy is highest (1 bit) before any view and falls with each view. "
   "IG(v) is the sum of entropies of the cells the viewpoint can see.",
   "<b>Uncertainty Unc(v).</b> For each visible cell, the uncertainty last recorded there by the detector (Section 4.6), faded by "
   "e<super>\u22120.6\u00b7n</super> so that re-viewing the same cell earns diminishing reward. This is what makes an unsure detection "
   "worth a second look.",
   "<b>Growth Growth(v).</b> The non-negative growth recorded in memory for the defects in view, with the same fading. This is "
   "the temporal term that lets a worsening defect attract the drone.",
   "<b>Staleness Stale(v).</b> 1 \u2212 e<super>\u22120.15\u00b7t</super> per cell, where <i>t</i> is the number of steps since the cell was last "
   "seen; it rises slowly, so a long-neglected area gradually becomes attractive (after the maximum-latency idea of Alamdari et al.).",
   "<b>Cost Cost(v).</b> Distance from the current viewpoint plus the small rotation term of Section 4.4."])
H3("4.9.2. The coverage guarantee")
P("While any wall has not been visited <i>in this mission</i>, the planner restricts itself to the viewpoints of the unvisited "
  "walls and scores them with the plain information-gain rule alone, IG(v) \u2212 0.4\u00b7Cost(v). Once every wall has been seen once, the "
  "full utility takes over. This was added after a surprising observation: Isler-NBV and every early UW-TIG variant stopped at "
  "exactly 4 of 9 walls on every seed. Since a planner with <i>none</i> of the new terms hit the same ceiling, no re-weighting of "
  "the new terms could fix it. In the cost-normalised greedy rule, flying to the far building is never worth its cost against the "
  "information gain still available nearby. A weight is a fragile thing to hang a guarantee on; an explicit phase is not.")
H3("4.9.3. Two-step lookahead")
P("In the full-utility phase, each candidate <i>v</i><sub>1</sub> is scored as U(v<sub>1</sub>) + 0.5\u00b7max<sub>v<sub>2</sub></sub> U(v<sub>2</sub> | after v<sub>1</sub>), "
  "where the second step uses the view counts that would result from visiting <i>v</i><sub>1</sub> but the current uncertainty, growth and "
  "staleness (a future detection cannot be simulated). Only the first step is executed, after which the planner re-plans, in the "
  "manner of a receding-horizon planner [24].")
H3("4.9.4. Why the terms fade with repeated views")
P("An early version let uncertainty and growth keep their full reward on every revisit. A real, persistent defect is re-detected on "
  "every look, so once found it earned its full reward again at no extra travel cost, and the lookahead exploited this so "
  "completely that flight distance collapsed to exactly 0.0 m for every UW-TIG variant: the planner camped on one viewpoint. Fading "
  "the terms with the view count, the same saturation used for coverage entropy, removed the exploit.")
H2("4.10. Reporting Rule and Metrics")
P("A planner\u2019s output for a mission is the set of (wall, class) pairs it <i>reports</i>. A pair is reported once it has been seen "
  "in at least three separate looks (counted across missions, since memory carries the count) or once at confidence \u2265 0.45; "
  "the rule is identical for every planner and was chosen on development seeds by planner-averaged F1. Precision, recall and F1 "
  "are computed over these reports against the scenario\u2019s ground truth, with classes that are really present in the photograph "
  "but are not the scenario\u2019s primary class <i>ignored</i> (as in COCO-style evaluation). Other metrics are mean localisation "
  "error (metres), total flight distance, wall coverage, reinspection rate, expected calibration error (ECE) of the detector\u2019s "
  "confidence, and an uncertainty gap (mean uncertainty on false positives minus on true positives). A \u201clegacy\u201d precision "
  "that divides unique true positives by every raw false-positive box is also kept, to show how much of the improvement is a "
  "change in measurement (Section 6.2).")
H2("4.11. Re-implemented Baselines")
P("Four published planners were added to the registry, each adapting the paper\u2019s viewpoint-selection rule to the same "
  "viewpoint graph and belief. They are faithful to the <i>rule</i>, not to the authors\u2019 full systems. Their parameters were "
  "set once from the papers\u2019 formulations and not tuned on any result.")
TABLE("4.2", "Re-implemented selection rules", ["Registry name", "Paper", "Selection rule"], [
    ["bircher_rhnbv", "Bircher et al. 2016", "Best depth-2 branch of gain \u00d7 e<super>\u22120.5\u00b7cost</super>; execute the first step only"],
    ["gatsbi_gtsp", "Dhami et al. (GATSBI)", "Nearest-neighbour + 2-opt tour over the least-inspected walls, followed in order"],
    ["ruckin_ipp", "R\u00fcckin et al. 2022\u201323", "Acquisition \u03a3(uncertainty, 0.5 if unobserved) / (1 + visit count), single-session belief"],
    ["alamdari_latency", "Alamdari et al. 2014", "Greedy on maximum time since last visit"],
    ["isler_nbv / random", "Isler et al. 2016 / none", "Cost-normalised entropy gain over unvisited views / uniform random"],
], [3.4 * cm, 3.6 * cm, 8.6 * cm], left=(0, 1, 2))
H2("4.12. Why PyBullet and Not Unity or Unreal")
P("A natural question is whether a game-engine or Gaussian-splatting renderer would make the simulation more convincing. A "
  "literature check suggests the answer is no <i>for this project</i>. AirSim [19], Flightmare [20] and GRaD-Nav [21] exist to close "
  "the gap between rendered and real imagery when a model is trained on synthetic images. Here the detector is trained and tested only on "
  "real photographs, applied as textures; the camera stays tightly framed on the wall under inspection and never sees the yard "
  "dressing. A better renderer would make the simulator prettier to watch but would not change one pixel that the detector learns "
  "from. PyBullet was therefore kept: it is scriptable from a terminal, runs headless in parallel, and gym-pybullet-drones "
  "already supplies PID flight. The honest limits \u2013 a software rasteriser, no sensor noise model, no wind \u2013 are listed in "
  "Section 6.8.")

# ================================================================ 5 SYSTEM IMPLEMENTATION
H1(5, "System Implementation", "System Implementation")
H2("5.1. Code Organisation")
TABLE("5.1", "Repository layout", ["Module", "Responsibility"], [
    ["sim_house.py; scene/environment.py", "Wall layout, textured quads, ground, sky, pipe rack, tower, props"],
    ["experiments/kinematic_capture.py", "Teleport-and-render camera for the statistical sweeps"],
    ["demo_uwtig_flight.py; make_comparison_video.py", "PID-flight demo; side-by-side planner videos"],
    ["datagen/mbdd_textures.py; prepare_mbdd.py; oversample_bulge.py", "MBDD2025 preparation, aspect-correct wall textures, class oversampling"],
    ["perception/ml_detector.py; train_yolo.py; train_yolo_gpu.py", "Detector with TTA uncertainty; CPU and GPU training"],
    ["geometry.py", "Camera matrices, pixel rays, wall planes, on-wall localisation"],
    ["memory/store.py", "PostgreSQL/pgvector log, Neo4j graph, identity matching and growth"],
    ["planning/viewpoints.py; planning/planners.py", "Viewpoint graph and cells; belief, UW-TIG, ablations and baselines"],
    ["experiments/scenarios.py; mission.py; evaluate.py", "Scenarios; the mission loop; scoring and the sweep driver"],
    ["experiments/diagnose_detection.py; tune_report_rule.py", "Planner-independent detector diagnostic; report-rule tuning on dev seeds"],
], [7.0 * cm, 8.6 * cm], left=(0, 1))
H2("5.2. Implementing the Simulation")
P("<b>Walls.</b> A single quad mesh (scene/wall_quad.obj) is scaled and rotated per wall, with its UV mapping chosen so that "
  "a texture pixel maps to a known world point; this analytic inverse was validated against the ray-plane path to under 2 cm "
  "for a known marker, and is used to score localisation error. <b>Lighting.</b> The capture call uses a fixed light direction "
  "with shadows enabled so that shading is consistent from view to view. <b>Textures.</b> Ground (concrete) and sky "
  "(gradient with a skyline silhouette) are generated procedurally at higher resolution than the first version; the sky is a backdrop "
  "around the yard so that the horizon is no longer a blank white void.")
P("<b>A tiling bug.</b> A texture-tiling bug in PyBullet\u2019s box geometry (GEOM_BOX) was found during the realism "
  "pass and fixed. <b>A resolution hypothesis that was wrong.</b> Because early recall was low, the first suspicion was image "
  "resolution. A higher camera and inference resolution was tried and <i>reduced</i> recall (0.42 to 0.22). The causes turned "
  "out to be texture distortion and viewing distance (Section 6.2), which would not have been found if the hypothesis had been "
  "accepted without measurement.")
H2("5.3. The Mission Loop")
P("Algorithm 1 summarises one mission (experiments/mission.py). The scenario sets the wall textures for this mission index "
  "and supplies ground truth; the belief is seeded from memory if the mission index exceeds one; then, for each of the "
  "16 steps, the planner chooses a viewpoint, the camera captures it, the detector runs, and each detection is localised, matched "
  "in memory, and written back into the belief.")
story.append(Preformatted(
    "Algorithm 1: one mission\n"
    "  belief <- MissionBelief(walls)\n"
    "  if mission > 1: belief.seed_from_memory(run_key)\n"
    "  scenario.setup_mission(mission)          # textures + ground truth\n"
    "  for step in 1..16:\n"
    "      v   <- planner.select_next(belief, current)\n"
    "      img <- camera.capture(v)\n"
    "      for d in detector(img):              # class, confidence, uncertainty\n"
    "          xyz  <- localize_on_wall(d.center, pose, wall)   # reject if off-wall\n"
    "          size <- distance(localize(d.corner1), localize(d.corner2))\n"
    "          id, growth <- memory.match_or_create(run_key, wall, d, xyz, size)\n"
    "          belief.record_detection(wall, xyz, d.uncertainty, growth)\n"
    "      belief.record_visit(v);  current <- v", S["code"]))
story.append(Spacer(1, 10))
H2("5.4. Experiment Harness and Protocol")
B(["<b>Development / test split.</b> Every design choice (viewpoint standoffs, reporting rule, fixes) was made on development "
   "seeds 100\u2013102. The reported numbers come from one run on test seeds 0\u20134 that was not tuned on.",
   "<b>Sweep size.</b> 4 scenarios \u00d7 12 planners \u00d7 5 seeds \u00d7 3 missions, 16 viewpoints per mission; results are "
   "averaged over static, uncertain and multi-defect (growing is reported separately).",
   "<b>Isolation.</b> Memory keys are namespaced as <i>scenario|planner|seed</i>. An early sweep let planners\u2019 detection "
   "histories leak into each other because identity matching was not scoped; this was caught by a targeted test and fixed before any "
   "reported number was produced.",
   "<b>Process isolation.</b> A single long process running about 140 mission-runs crashed three times with three different symptoms "
   "(allocation failure, silent exit, segmentation fault), consistent with PyBullet\u2019s software renderer accumulating resources over "
   "many render sessions. Each seed now runs in its own subprocess and the per-seed CSVs are merged (run_full_sweep.sh).",
   "<b>Parallel sweeps.</b> For the 31-wall yard each (seed, scenario) pair is a separate subprocess and fourteen run at once "
   "(experiments/run_parallel_sweep.py); the parts are concatenated into one CSV. Each large sweep is 240 rows and took about 30 minutes."])
H2("5.5. Debugging Episodes")
P("Four defects in the work itself shaped the final design, and are recorded here because each changed a conclusion.")
B(["<b>Camping.</b> The lookahead exploited non-decaying uncertainty/growth rewards (flight distance 0.0 m). Fixed by fading the terms with view count (Section 4.9.4).",
   "<b>Free spinning.</b> Building B\u2019s coincident viewpoints made turning in place free. An over-large rotation cost fixed it but collapsed "
   "Isler-NBV\u2019s coverage from 0.875 to 0.333; the final constant (1/3600 m per degree) breaks only exact ties.",
   "<b>Cells.</b> A fixed cell count per wall froze the planner on narrow panels; fixed physical cell width fixed it (Section 4.4).",
   "<b>Wrong-surface hits.</b> Ray hits outside the wall\u2019s rectangle were blamed on the inspected wall (Section 4.7)."])
H2("5.6. Demonstration and Comparison Videos")
P("demo_uwtig_flight.py flies a chosen planner under real PID control through three missions of the multi-defect scenario, "
  "writing a third-person flythrough and an onboard-camera video with detections, confidences and uncertainties overlaid. "
  "make_comparison_video.py splices the flythrough or inspection videos of different planners frame-by-frame, because the step "
  "count depends on the budget and mission count, not on the planner. Fig. 5.1 is one such frame.")
FIG(os.path.join(HERE, "comparison_flythrough_frame.png"), 14.2 * cm, "5.1", "Same scenario, seed and timestep, three planners (left to right: UW-TIG, Isler-NBV, Random)")
FIG(os.path.join(HERE, "inspection_frame.png"), 7.2 * cm, "5.2", "Onboard camera frame from the demonstration: real corrosion detections with confidence and uncertainty")

# ================================================================ 6 RESULTS
H1(6, "Experimental Results", "Experimental Results")
H2("6.1. Detector Benchmark")
P("The detector is evaluated on the held-out MBDD2025 test split of 1,448 images. Two checkpoints were trained: a CPU baseline "
  "(YOLOv8n, 320 px, 30 epochs) and the default GPU model (YOLOv8s, 640 px, 100 epochs, with the rarest class, bulge, "
  "oversampled about four times). A later YOLO11m retrain on the same GPU was evaluated but not adopted.")
TABLE("6.1", "Detector results on the held-out test set (1,448 images)", ["Model", "mAP50", "mAP50-95", "Precision", "Recall"], [
    ["YOLOv8n, 320 px, 30 epochs (CPU)", "0.685", "0.347", "0.804", "0.612"],
    ["YOLOv8s, 640 px, 100 epochs (default)", "0.884", "0.506", "0.874", "0.842"],
    ["YOLO11m, 640 px (retrain; not adopted)", "0.890", "0.510", "0.869", "0.863"],
], [6.6 * cm, 2.2 * cm, 2.4 * cm, 2.2 * cm, 2.2 * cm], left=(0,), bold_row=1)
P("<b>Model-size comparison under identical settings.</b> The rows above differ in resolution, epochs and data, so they are not a fair size comparison. "
  "YOLOv8n, v8s and v8m were therefore retrained with exactly the same recipe: the same fixed random subset of 4,000 MBDD2025 training images, "
  "640 px, 30 epochs, batch 8, seed 0, no oversampling, on one RTX 5060 GPU (datagen/compare_detectors.py), and all three were scored on the full 1,448-image test split. "
  "YOLOv8l was not trained (8 GB of GPU memory). Each model was trained once, so differences of a few thousandths are within run-to-run noise.")
TABLE("6.1b", "YOLOv8 size comparison, identical subset training (4,000 images, 30 epochs, 640 px)", ["Model", "Parameters", "mAP50", "mAP50-95", "Precision", "Recall"], [
    ["YOLOv8n", "3.0 M", "0.743", "0.373", "0.786", "0.681"],
    ["YOLOv8s", "11.1 M", "0.793", "0.411", "0.803", "0.740"],
    ["YOLOv8m", "25.8 M", "0.796", "0.418", "0.802", "0.744"],
], [4.0 * cm, 2.8 * cm, 2.4 * cm, 2.6 * cm, 2.4 * cm, 2.4 * cm], left=(0,))
P("Going from n to s gives +0.050 mAP50; going from s to m gives only +0.003, which is inside run-to-run noise, for 2.3 times the parameters. "
  "YOLOv8s is therefore the sensible default: nearly all of the gain from model size is reached at the small size. These subset-trained scores "
  "(0.74 to 0.80) are lower than the default detector's 0.884 because that model saw all 12,955 training images for 100 epochs.")
FIG(os.path.join(FIGS, "class_chart.png"), 11.0 * cm, "6.1", "Per-class precision and recall of the default detector")
P("Crack is the hardest class (recall 0.75): cracks are thin, low-contrast features that lose most of their signal at low "
  "resolution, which is why moving from 320 px to 640 px nearly doubled crack recall. Bulge, the best class (0.95 / 0.96), "
  "was the rarest in the data and was oversampled. The default detector does <i>not</i> reach 0.90 on mean precision or recall; "
  "all the above-0.90 numbers in this report are closed-loop report-level metrics (Section 6.3), not detector metrics. Compared "
  "with the literature, this detector is below the single-class and private-data scores of Section 2.1.4 and above the "
  "recall of Huang et al.\u2019s crack detector (0.766) on a harder five-class public task.")
H2("6.2. How the Closed-Loop Numbers Reached 0.90")
P("The first complete sweep gave UW-TIG 0.76 precision, 0.63 recall and 0.65 F1. Rather than tune the planner, we asked whether the "
  "<i>measurement</i> was right. Five problems were diagnosed on development seeds 100\u2013102, each affecting every planner equally:")
TABLE("6.2", "The five fixes", ["#", "Problem", "Fix"], [
    ["1", "Precision divided unique true positives by every raw false-positive box, penalising reinspection itself", "Score per inspection report (3 looks across missions, or one at confidence \u2265 0.45)"],
    ["2", "16% of photos hold a second real defect; detecting it counted as a false positive", "Ignore classes present in the photo, COCO-style"],
    ["3", "Textures stretched ~2.2\u00d7 and pixelated", "Aspect-correct crop at 1536 px; square-pixel frames"],
    ["4", "Single-look recall 0.47 at 0.8 m, 0.85 at 1.3 m, 0.97 at 1.8 m, 0.99 at 2.2 m", "Replace the 0.8/1.3 m tiers with 1.3 m and 2.2 m"],
    ["5", "Hits outside the wall rectangle blamed on the inspected wall (51\u201375% of false positives)", "Reject hits off the wall (+5 cm)"],
], [0.8 * cm, 8.2 * cm, 6.6 * cm], left=(1, 2))
FIG(os.path.join(FIGS, "dev_progress.png"), 11.5 * cm, "6.2", "UW-TIG on development seeds as the fixes were applied")
P("Development progression (precision / recall / F1): original 0.76 / 0.63 / 0.65; fixes 1\u20133 0.88 / 0.78 / 0.82; plus the "
  "survey standoff 0.86 / 0.96 / 0.90; plus the on-wall check 0.95 / 0.99 / 0.97. The honest reading is that <b>a large part of "
  "the gain is measurement, not planning</b>: under the old scoring formula the final UW-TIG precision on test seeds would be "
  f"{f3(M('uwtig','precision_legacy'))}.")
H2("6.3. Closed-Loop Comparison and Ablations")
abl = [("uwtig", "UW-TIG (full)"), ("uwtig_no_uncertainty", "no uncertainty term"), ("uwtig_no_temporal", "no temporal (growth) term"),
       ("uwtig_no_staleness", "no staleness term"), ("uwtig_no_lookahead", "no lookahead"), ("uwtig_no_coverage_first", "no coverage phase")]
TABLE("6.3", "UW-TIG and its ablations on test seeds 0\u20134 (mean over static, uncertain, multi-defect; confirmed reports)",
      ["Planner", "Precision", "Recall", "F1", "Loc. err (m)", "Flight (m)", "Coverage"],
      [[n, f3(M(p, "precision_confirmed")), f3(M(p, "recall_confirmed")), f3(M(p, "f1_confirmed")),
        f2(M(p, "mean_localization_error_m")), f1(M(p, "total_flight_dist_m")), f2(M(p, "coverage_frac"))] for p, n in abl],
      [4.6 * cm, 2.0 * cm, 1.8 * cm, 1.8 * cm, 2.2 * cm, 2.0 * cm, 1.8 * cm], bold_row=0)
FIG(os.path.join(FIGS, "ablation_chart.png"), 14.0 * cm, "6.3", "Recall and flight distance of the ablations")
P(f"UW-TIG reaches precision {f3(UWp)}, recall {f3(UWr)} and F1 {f3(UWf)}. By scenario (precision / recall / F1) it scores "
  "static 0.964 / 0.933 / 0.940, uncertain 0.893 / 0.967 / 0.925 and multi-defect 0.989 / 1.000 / 0.995; the per-seed F1 values are "
  "0.943, 0.890, 1.000, 1.000 and 0.933. <b>The averages clear 0.90, but not every slice does</b>: the deliberately faint "
  "uncertain scenario is at 0.893 precision and one test seed is at F1 0.890.")
P("The <b>coverage guarantee is the decisive component</b>: without it recall falls from 0.967 to 0.556 and F1 from 0.953 to 0.680, "
  "with coverage back at 0.44 (4 of 9 walls). Two ablations are slightly <i>better</i> than the full planner: without staleness or "
  "without the lookahead, precision is 0.967, localisation error 0.57\u20130.59 m and flight 32\u201336% shorter, because once a single "
  "survey look at 2.2 m is about 99% reliable, revisiting for staleness or planning ahead adds flying but not accuracy.")
H2("6.4. Why Removing Uncertainty or Growth Changes Nothing")
P("Table 6.3 shows that the no-uncertainty and no-growth ablations are identical, or nearly so, to the full planner. We checked "
  "the code rather than assume, and found two reasons.")
B(["<b>The coverage phase never evaluates these terms.</b> While any wall is unvisited, the planner scores only IG \u2212 0.4\u00b7Cost. With nine "
   "walls and a 16-viewpoint budget, roughly half of every mission is spent there, and the three missions of a seed each re-run "
   "this phase because it is defined per mission.",
   "<b>Growth is near zero by construction in these scenarios.</b> Growth is the change in a defect\u2019s measured size, clipped to be "
   "non-negative; static, uncertain and multi-defect defects never grow, so growth is only detector noise around a constant. "
   "Removing the term leaves flight distance bit-identical (125.1 m).",
   "<b>Uncertainty is real but small.</b> The TTA spread is typically 0.1\u20130.3, so 1.5\u00d7 that is small beside the other terms. "
   "Removing it shifts the path slightly (124.6 m against 125.1 m) but not how many looks each wall gets, which is all that "
   "confirmed precision and recall depend on."])
P("This is an open finding, not a vindication: it means that in the current configuration two of the four novel mechanisms do not yet "
  "influence the outcome, and that re-weighting them, or testing on scenarios with real growth, is the next step (Chapter 7).")
H2("6.5. Head-to-Head with Published Planners")
pl = [("random", "Random baseline"), ("isler_nbv", "Isler-NBV (classical, 2016)"), ("bircher_rhnbv", "Bircher et al. 2016"),
      ("gatsbi_gtsp", "Dhami et al. (GATSBI)"), ("alamdari_latency", "Alamdari et al. 2014"), ("ruckin_ipp", "R\u00fcckin et al. 2023"),
      ("uwtig", "UW-TIG (ours)")]
TABLE("6.4", "Planner comparison on test seeds 0\u20134 (confirmed reports)",
      ["Planner", "Prec.", "Recall", "F1", "F1 1-look", "Loc. err (m)", "Flight (m)", "Cov."],
      [[n, f3(M(p, "precision_confirmed")), f3(M(p, "recall_confirmed")), f3(M(p, "f1_confirmed")), f3(M(p, "f1")),
        f2(M(p, "mean_localization_error_m")), f1(M(p, "total_flight_dist_m")), f2(M(p, "coverage_frac"))] for p, n in pl],
      [4.1 * cm, 1.7 * cm, 1.5 * cm, 1.4 * cm, 1.8 * cm, 1.8 * cm, 1.7 * cm, 1.6 * cm], bold_row=6)
FIG(os.path.join(FIGS, "planner_chart.png"), 14.2 * cm, "6.4", "F1 and flight distance of all compared planners")
P(f"<b>UW-TIG ties the strongest planner, R\u00fcckin\u2019s IPP, on detection quality</b> (F1 {f3(UWf)} against {f3(RKf)}, well inside the "
  f"seed-to-seed spread, UW-TIG\u2019s own per-seed F1 spanning 0.890 to 1.000). <b>Where it differs is cost</b>: {f1(UWfly)} m of flight "
  f"against {f1(RKfly)} m, {FLYLESS}% less, with the lowest localisation error of the seven planners. R\u00fcckin\u2019s rule has slightly higher "
  "precision (0.959 against 0.949), which supports uncertainty-driven acquisition as a strong rule. The published rules that fail "
  "(Isler, Bircher) fail on <i>coverage</i>, 0.44 and 0.67 of the walls, the same cost-scale ceiling the coverage phase removes. These "
  "are selection-rule re-implementations, not the authors\u2019 systems, and no number from the original papers is reproduced or claimed.")
H2("6.6. Calibration of the Uncertainty Signal")
P("The study of R\u00fcckin et al.\u2019s evaluation prompted a check we had not run on ourselves: is the uncertainty UW-TIG weights "
  "informative, and is the detector\u2019s confidence calibrated? Across all twelve planners the expected calibration error is "
  "0.29\u20130.33, far above a calibrated model, and the uncertainty gap is <i>negative</i> for every planner (\u22120.12 to \u22120.08): "
  "uncertainty is on average slightly <i>lower</i> on false positives than on true positives. A plausible, unconfirmed explanation "
  "is that real, hard-to-see defects sit near the decision boundary and vary more under photometric perturbation than a "
  "consistently mis-recognised texture. The signal is used only to rank views within a mission, never as a probability, so the "
  "measured precision and recall stand; but the claim that high uncertainty means \u201clikely wrong\u201d is not supported.")
P("We also checked whether switching to MC-Dropout is a simple fix. In the installed Ultralytics, stock YOLOv8/v11 detection "
  "models contain no dropout layer anywhere (it exists only in the classification head). A true MC-Dropout would need dropout "
  "spliced into the neck or head through a custom model definition, a full retrain, and has no guarantee of better calibration, "
  "since dropout variance is known to track correctness poorly on confident, well-converged detectors. It is therefore listed as future work.")
H2("6.7. The Growing Scenario")
P("In the growing scenario the detector recalls essentially nothing. Its defect is a procedural corrosion texture, and a detector trained "
  "only on real photographs does not recognise it (zero detections above confidence 0.1 on the rendered frame, checked directly). "
  "The memory mechanism itself was verified in isolation \u2013 a defect re-detected at a shifted position and larger size was matched "
  "and its growth computed, while a distant detection created a new identity \u2013 so the failure is the detector\u2019s domain "
  "generalisation, not the memory. For this reason the growing scenario is excluded from the comparison tables and the growth term "
  "has not yet been shown to help.")
H2("6.8. A Broader Detector: Multi-Dataset Fine-Tuning")
P("The first detector was trained on MBDD2025 alone. To see whether public data from other sources would help, the same YOLOv8s "
  "weights were fine-tuned for 30 epochs (AdamW, learning rate 0.0005, batch 32, 640 px, early stopping on a combined validation set) on "
  "MBDD2025 plus the dacl10k and Roboflow corrosion images of Table 3.2, and both detectors were scored on three test sets (Table 6.5). "
  "The weights, merged-dataset builder and evaluation script are in the repository (datagen/prepare_extra.py, datagen/eval_extra.py).")
_o, _n = DET["old"], DET["new"]
TABLE("6.5", "Original and fine-tuned detector on three test sets", ["Test set", "Metric", "Original", "Fine-tuned"], [
    ["MBDD2025 test (1,448)", "mAP50", f3(_o["mbdd"]["map50"]), f3(_n["mbdd"]["map50"])],
    ["", "mAP50-95", f3(_o["mbdd"]["map50_95"]), f3(_n["mbdd"]["map50_95"])],
    ["", "Precision / recall", f"{f3(_o['mbdd']['p'])} / {f3(_o['mbdd']['r'])}", f"{f3(_n['mbdd']['p'])} / {f3(_n['mbdd']['r'])}"],
    ["dacl10k held-out (810)", "mAP50", f3(_o["dacl"]["map50"]), f3(_n["dacl"]["map50"])],
    ["", "mAP50-95", f3(_o["dacl"]["map50_95"]), f3(_n["dacl"]["map50_95"])],
    ["", "Precision / recall", f"{f3(_o['dacl']['p'])} / {f3(_o['dacl']['r'])}", f"{f3(_n['dacl']['p'])} / {f3(_n['dacl']['r'])}"],
    ["Concrete-crack crops (400 + 400)", "Crack recall", f"{_o['crack_presence']['recall']:.3f}", f"{_n['crack_presence']['recall']:.3f}"],
    ["", "False-alarm rate", f"{_o['crack_presence']['false_alarm_rate']:.3f}", f"{_n['crack_presence']['false_alarm_rate']:.3f}"],
], [4.4 * cm, 3.6 * cm, 3.3 * cm, 3.3 * cm], left=(0, 1))
FIG(os.path.join(FIGS, "detector_chart.png"), 9.0 * cm, "6.5", "mAP50 of the original and fine-tuned detector on the MBDD2025 and dacl10k test sets")
P(f"<b>The gain is on the new data, not the old.</b> On dacl10k\u2019s held-out images the original detector scores almost nothing "
  f"({_o['dacl']['map50']:.3f} mAP50): bridge-inspection close-ups of the kind dacl10k contains are far from MBDD2025\u2019s UAV photographs. After "
  f"fine-tuning it reaches {_n['dacl']['map50']:.3f}, with the largest per-class gain on corrosion "
  f"({_n['dacl']['per_class_ap50']['corrosion']:.3f}) and crack ({_n['dacl']['per_class_ap50']['crack']:.3f}). That is still a low score in "
  "absolute terms; dacl10k is a hard benchmark whose published baselines are segmentation models with a best mean IoU of 0.42 [28], "
  f"and the mapping of its classes onto ours is imperfect. On MBDD2025 the score is unchanged within noise ({_o['mbdd']['map50']:.3f} against "
  f"{_n['mbdd']['map50']:.3f} mAP50, mAP50-95 {_o['mbdd']['map50_95']:.3f} against {_n['mbdd']['map50_95']:.3f}), so the extra data neither "
  "hurt nor helped the original domain.")
P(f"<b>The crack-presence check is a negative result.</b> On 800 held-out concrete crops neither detector finds cracks "
  f"(recall {_o['crack_presence']['recall']:.3f} and {_n['crack_presence']['recall']:.3f}, no false alarms). These 227-pixel close-ups "
  "have no context and a texture far from either training set, and our detector was trained on boxes around cracks in larger scenes. "
  "We report it as a limitation of the check rather than as evidence either way; it does not show that the detector would miss such "
  "cracks if framed differently, only that this kind of image is out of distribution. SDNET2018, had it been obtainable, "
  "would have posed the same problem.")

H2("6.9. Scaling the Evaluation to a 31-Wall Yard")
P("Every planner and ablation was re-run in the 31-wall yard (Section 4.2.0) on the same test seeds 0\u20134, with a budget of 50 steps and three "
  "missions per scenario, using the original detector. As elsewhere, the average covers the static, uncertain and multi-defect scenarios; "
  "the growing scenario is excluded. The confidence intervals below are 95% bootstrap intervals over the five seeds, each seed\u2019s value being "
  "its mean over scenarios, because rows from the same seed are not independent.")
_order = [("uwtig", "UW-TIG (ours)"), ("alamdari_latency", "Alamdari et al. 2014"), ("gatsbi_gtsp", "Dhami et al. (GATSBI)"),
          ("ruckin_ipp", "R\u00fcckin et al. 2023"), ("random", "Random"), ("bircher_rhnbv", "Bircher et al. 2016"), ("isler_nbv", "Isler-NBV (classical)")]
TABLE("6.6", "Planners in the 31-wall yard, original detector (test seeds 0\u20134, confirmed reports)",
      ["Planner", "Prec.", "Recall", "F1", "F1 95% CI", "Flight (m)", "Cov."],
      [[n, f3(SP("large_old", p, "precision_confirmed")), f3(SP("large_old", p, "recall_confirmed")), f3(SP("large_old", p, "f1_confirmed")),
        f"{SP('large_old', p, 'f1_ci')[0]:.3f}\u2013{SP('large_old', p, 'f1_ci')[1]:.3f}", f"{SP('large_old', p, 'total_flight_dist_m'):.0f}",
        f2(SP("large_old", p, "coverage_frac"))] for p, n in _order],
      [4.2 * cm, 1.5 * cm, 1.6 * cm, 1.5 * cm, 2.6 * cm, 2.0 * cm, 1.4 * cm], bold_row=0)
FIG(os.path.join(FIGS, "f1_by_yard.png"), 15.0 * cm, "6.6", "F1 and flight distance of each planner in the 9-wall and the 31-wall yard (flight on a log axis)")
_a = SD("large_old", "alamdari_latency"); _g = SD("large_old", "gatsbi_gtsp"); _r = SD("large_old", "ruckin_ipp"); _x = SD("large_old", "random")
P(f"<b>The ordering mostly survives, but the margins shrink.</b> UW-TIG\u2019s F1 falls from {f3(SP('small_old', 'uwtig', 'f1_confirmed'))} to "
  f"{f3(SP('large_old', 'uwtig', 'f1_confirmed'))} when the yard grows from 9 to 31 walls, as does every planner\u2019s that reaches full "
  f"coverage. The paired per-seed differences (Table 6.7, Fig. 6.7) show UW-TIG statistically indistinguishable from Alamdari\u2019s "
  f"latency rule ({_a[0]:+.3f}, interval {_a[1]:+.3f} to {_a[2]:+.3f}) and from GATSBI ({_g[0]:+.3f}, {_g[1]:+.3f} to {_g[2]:+.3f}), "
  f"ahead of R\u00fcckin\u2019s IPP by {_r[0]:+.3f} (interval {_r[1]:+.3f} to {_r[2]:+.3f}, excluding zero, winning {_r[3]} of {_r[4]} seeds) and far ahead of "
  f"random search ({_x[0]:+.3f}, all {_x[4]} seeds). The advantage that remains is cost: UW-TIG flies {SP('large_old', 'uwtig', 'total_flight_dist_m'):.0f} m "
  f"against {SP('large_old', 'ruckin_ipp', 'total_flight_dist_m'):.0f} m for IPP and {SP('large_old', 'alamdari_latency', 'total_flight_dist_m'):.0f} m for the latency rule, "
  f"and {SP('large_old', 'random', 'total_flight_dist_m'):.0f} m for random search. In this yard UW-TIG therefore ties the best "
  "detection score at lower flight cost, rather than beating every rival outright.")
TABLE("6.7", "UW-TIG minus each planner, F1 per seed (31-wall yard, original detector)",
      ["Versus", "Mean difference", "95% interval", "Seeds won"],
      [[n, f"{SD('large_old', p)[0]:+.3f}", f"{SD('large_old', p)[1]:+.3f} to {SD('large_old', p)[2]:+.3f}", f"{SD('large_old', p)[3]} of {SD('large_old', p)[4]}"]
       for p, n in _order[1:]], [5.4 * cm, 3.4 * cm, 4.2 * cm, 2.6 * cm], left=(0,))
FIG(os.path.join(FIGS, "paired_chart.png"), 11.5 * cm, "6.7", "Paired F1 difference between UW-TIG and each planner in the 31-wall yard, with 95% bootstrap intervals")
P(f"<b>The coverage guarantee still decides the outcome.</b> The three planners without an explicit coverage mechanism visit only a "
  f"fraction of the walls (Isler-NBV {SP('large_old', 'isler_nbv', 'coverage_frac'):.2f}, Bircher {SP('large_old', 'bircher_rhnbv', 'coverage_frac'):.2f}, "
  f"UW-TIG without the coverage phase {SP('large_old', 'uwtig_no_coverage_first', 'coverage_frac'):.2f}) and their F1 collapses to "
  f"{f3(SP('large_old', 'isler_nbv', 'f1_confirmed'))}, {f3(SP('large_old', 'bircher_rhnbv', 'f1_confirmed'))} and "
  f"{f3(SP('large_old', 'uwtig_no_coverage_first', 'f1_confirmed'))}. The cost-normalised greedy ceiling is therefore not an artefact of "
  "the small yard; it gets worse as the yard grows.")
TABLE("6.8", "UW-TIG ablations in the 31-wall yard (original detector)", ["Variant", "Prec.", "Recall", "F1", "Flight (m)", "Cov."],
      [[n, f3(SP("large_old", p, "precision_confirmed")), f3(SP("large_old", p, "recall_confirmed")), f3(SP("large_old", p, "f1_confirmed")),
        f"{SP('large_old', p, 'total_flight_dist_m'):.0f}", f2(SP("large_old", p, "coverage_frac"))]
       for p, n in [("uwtig", "Full UW-TIG"), ("uwtig_no_uncertainty", "no uncertainty"), ("uwtig_no_temporal", "no growth"),
                    ("uwtig_no_staleness", "no staleness"), ("uwtig_no_lookahead", "no lookahead"), ("uwtig_no_coverage_first", "no coverage phase")]],
      [4.6 * cm, 1.7 * cm, 1.8 * cm, 1.7 * cm, 2.3 * cm, 1.7 * cm], bold_row=0)
P(f"The ablation pattern repeats from the small yard. Removing uncertainty or growth changes F1 by less than 0.005 and the flight by under a "
  f"metre; removing staleness or lookahead shortens the flight (to {SP('large_old', 'uwtig_no_staleness', 'total_flight_dist_m'):.0f} m and "
  f"{SP('large_old', 'uwtig_no_lookahead', 'total_flight_dist_m'):.0f} m, against {SP('large_old', 'uwtig', 'total_flight_dist_m'):.0f} m) at no "
  "measurable cost in F1. Together with Section 6.4 this means that, on both yard sizes, two of the five novel mechanisms (uncertainty and "
  "growth) do not yet change any reported number, and two more (staleness and lookahead) cost distance without buying accuracy. Only the "
  "coverage phase is demonstrably necessary. The honest reading is that the planner\u2019s measured contribution is the coverage guarantee "
  "plus a competitive, cost-aware utility, and that the remaining terms await scenarios that exercise them.")

H2("6.10. Does a Broader Detector Improve the Closed Loop?")
P("The natural expectation is that a detector fine-tuned on more data improves the planner that depends on it. To test it, the "
  "complete sweep was repeated with the fine-tuned weights in both yards (Table 6.9).")
TABLE("6.9", "UW-TIG with the original and the fine-tuned detector", ["Yard", "Detector", "Prec.", "Recall", "F1", "Flight (m)"],
      [[y, d, f3(SP(k, "uwtig", "precision_confirmed")), f3(SP(k, "uwtig", "recall_confirmed")), f3(SP(k, "uwtig", "f1_confirmed")),
        f"{SP(k, 'uwtig', 'total_flight_dist_m'):.0f}"]
       for y, d, k in [("9 walls", "original", "small_old"), ("9 walls", "fine-tuned", "small_new"),
                       ("31 walls", "original", "large_old"), ("31 walls", "fine-tuned", "large_new")]],
      [2.6 * cm, 3.2 * cm, 2.0 * cm, 2.2 * cm, 2.0 * cm, 2.6 * cm])
P(f"<b>It does not.</b> UW-TIG\u2019s F1 is {f3(SP('small_new', 'uwtig', 'f1_confirmed'))} with the fine-tuned detector in the 9-wall yard against "
  f"{f3(SP('small_old', 'uwtig', 'f1_confirmed'))} with the original, and {f3(SP('large_new', 'uwtig', 'f1_confirmed'))} against "
  f"{f3(SP('large_old', 'uwtig', 'f1_confirmed'))} in the 31-wall yard; the other planners move by similar amounts in the same direction. Two reasons are plausible, "
  "and we have not separated them. First, the simulator\u2019s wall textures are MBDD2025 photographs, so the closed loop only ever tests the "
  "domain on which the two detectors are equal; dacl10k\u2019s gain cannot show up. Second, fine-tuning on a differently framed dataset may have "
  "slightly displaced the confidence calibration that the reporting rule (Section 4.10) was tuned on, which would lower the "
  "confirmed-report scores without lowering mAP. Either way, the decision is clear: <b>the original detector stays the default</b>, "
  "the headline numbers of this report use it, and the fine-tuned weights are reported as a separate, partial result. Using the dacl10k "
  "gain in the closed loop would need dacl10k-like wall textures in the simulator and a re-tuned reporting rule.")

H2("6.11. Planner-Only Tests: Oracle Detector, Weight Sensitivity and Ten Seeds")
P("Section 6.4 found that switching off the uncertainty and growth terms changes nothing. Two explanations remain: the real detector gives too weak a "
  "signal, or the terms are too weak at their weights (1.5 and 2.0). Both were tested. An <b>oracle detector</b> (perception/oracle_detector.py) reads the "
  "scenario's ground truth and returns detections with controlled noise (15% misses, confidence rising with severity, faint defects more uncertain, "
  "defects that really grow). It is a synthetic planner-only test and says nothing about real detection quality.")
B(["<b>Oracle, both yards, 5 seeds.</b> The no-uncertainty and no-growth variants are identical to full UW-TIG in route and F1 (9 walls: 124.6 m; "
   "31 walls: 480 m, F1 0.871 against 0.870 and 0.871). In the growing scenario every variant detects the growth (fraction 1.0), including the one without the growth term, "
   "because the coverage and revisit logic already finds it.",
   "<b>Weight sensitivity.</b> Setting both weights to 0, 6 and 20 leaves F1 unchanged (oracle detector, static, uncertain and growing scenarios; 9 walls: 0.918 in all three; 31 walls: 0.822, 0.821, 0.820). "
   "The terms do not change the route even when they dominate the score.",
   "<b>Staleness and lookahead.</b> Without them the flight is shorter (9 walls: 81 to 83 m against 125 m; 31 walls: 417 and 446 m against 481 m). "
   "With the real detector the confirmed F1 does not fall: on the 9-wall yard it is higher, 0.973 against 0.963 (paired +0.010 in favour of removing them, "
   "95% CI +0.003 to +0.017, all 10 seeds); on the 31-wall yard it is 0.925 and 0.920 against 0.921, a tie. With the oracle detector F1 falls slightly "
   "(31 walls 0.862 and 0.864 against 0.871). These two terms therefore cost flight, and in the 9-wall yard they cost a little detection quality as well.",
   "<b>Ten seeds, original detector, confirmed F1 (seeds 0-9; experiments/analyze_ten_seeds.py).</b> 9-wall yard: UW-TIG 0.963 (95% CI 0.941 to 0.982) at 125 m; "
   "Alamdari 0.951 at 168 m; Rückin 0.938 at 206 m; GATSBI 0.914; random 0.891 at 379 m; Bircher 0.816; Isler 0.663; no coverage phase 0.679. "
   "UW-TIG minus Alamdari is +0.012 (CI +0.001 to +0.022, 6 of 10 seeds) and minus Rückin +0.025 (CI -0.002 to +0.055, 4 of 10): a small, borderline "
   "lead over Alamdari and not significant over Rückin. 31-wall yard: Alamdari 0.928 at 570 m; UW-TIG 0.921 (0.908 to 0.933) at 481 m; GATSBI 0.917 at 471 m; "
   "Rückin 0.906 at 846 m; random 0.827 at 2,396 m; Bircher 0.664; no coverage phase 0.658; Isler 0.474. UW-TIG is level with Alamdari (-0.007, CI -0.014 to 0.000) "
   "and GATSBI (+0.004, -0.005 to +0.013) and ahead of Rückin by +0.014 (+0.001 to +0.029) with 43% less flight. In both yards the no-uncertainty and no-growth "
   "variants differ from UW-TIG by 0.002 or less."])
P("Conclusion of these tests: the coverage-first phase and cost-aware routing carry UW-TIG's results. The uncertainty and growth terms, the parts that "
  "make the planner <i>uncertainty-weighted</i> and <i>temporal</i>, show no measurable benefit in this simulator and are reported as untested extensions, "
  "not as demonstrated contributions.")

H2("6.12. Threats to Validity")
B(["<b>Selection-rule baselines.</b> The compared planners are re-implemented rules, not full systems.",
   "<b>Five seeds.</b> Ten seeds per yard are enough to see the coverage effect, but UW-TIG is only level with the best rivals (Alamdari in both yards, GATSBI at 31 walls) and is not significantly ahead of Rückin in the 9-wall yard.",
   "<b>Measurement versus planning.</b> Five fixes in measurement raised every planner; the improvement over the first sweep should not be read as a planning gain.",
   "<b>Simulation realism.</b> A software rasteriser, flat-quad walls, no wind or sensor noise, a kinematic mode without dynamics; absolute detector scores would differ outdoors.",
   "<b>Single-time-point data.</b> MBDD2025 has no growth sequences, so temporal claims rest on one procedural scenario the detector cannot see.",
   "<b>Scale-up caveats.</b> The 31-wall yard uses the same flat-quad walls, the same reporting rule (tuned on the small yard) and a budget of 50 chosen from one pilot run, not tuned; defect placement is random per seed, so the 31-wall and 9-wall numbers differ in layout as well as size.",
   "<b>Class mapping.</b> The dacl10k-to-MBDD2025 class mapping is a judgement (Section 3.3); the dacl10k scores depend on it.",
   "<b>Memory port.</b> The 31-wall sweeps used the in-process memory store, a port of the matching rule that was not cross-checked against the database version on the same sweep."])

# ================================================================ 7 FUTURE SCOPE
H1(7, "Future Scope and Enhancements", "Future Scope & Enhancements")
B(["<b>Make the novel terms matter.</b> Re-weight or normalise the uncertainty and growth terms, and evaluate on scenarios with real "
   "growth, so that the ablations in Section 6.4 separate.",
   "<b>Better uncertainty.</b> Try post-hoc temperature scaling first; then prototype MC-Dropout by splicing dropout into the detection head and "
   "retraining.",
   "<b>Close the growing-defect gap.</b> Mix synthetic defect imagery into training (as synth-dacl [29] does for bridge segmentation), or obtain a longitudinal "
   "real dataset; SDNET2018 was planned but its download is bot-protected.",
   "<b>Use the broader detector in the loop.</b> Texture the simulator with dacl10k-style close-ups, re-tune the reporting rule for the fine-tuned detector, and re-run Table 6.9.",
   "<b>Lift the weak slices.</b> Raise the uncertain scenario\u2019s precision above 0.90 through scenario-specific confirmation-rule tuning, and "
   "narrow R\u00fcckin\u2019s precision lead by re-weighting utility terms.",
   "<b>Fuller baselines.</b> Re-implement the compared papers, and IA-TIGRIS (2026), as full systems with sampling-based planning and "
   "online retraining.",
   "<b>More seeds</b> for the ablations, and a decision whether staleness and lookahead stay on by default.",
   "<b>Richer simulation.</b> Pipe segments and truss rigs as first-class inspectable geometry; sensor noise and wind; a Gaussian-splatting "
   "or game-engine renderer if the work moves to training on synthetic imagery.",
   "<b>A stronger detector.</b> The YOLO11m retrain (mAP50 0.890, precision 0.869, recall 0.863) is a marginal, mixed gain; adopting it "
   "requires re-running the sweep. YOLOv8m/l and 1280 px were not tried."])

# ================================================================ 8 CONCLUSION
H1(8, "Conclusion", "Conclusion")
P(f"This project built and measured a planner that knows what a defect is. UW-TIG combines an information-gain term "
  f"with a coverage guarantee, detector uncertainty, cross-mission defect memory with growth, revisit staleness and a "
  f"two-step lookahead, and was evaluated on a simulation testbed built for the purpose. On held-out test seeds it reaches precision "
  f"{f3(UWp)}, recall {f3(UWr)} and F1 {f3(UWf)}, above 0.90 on all three, which neither the classical information-gain baseline nor random search reaches, "
  f"and it ties the strongest of five re-implemented published planners while flying {FLYLESS}% less.")
P(f"The work was then stress-tested in two directions. Enlarging the yard from 9 to 31 walls lowers every planner\u2019s F1 (UW-TIG: {f3(SP('small_old', 'uwtig', 'f1_confirmed'))} to "
  f"{f3(SP('large_old', 'uwtig', 'f1_confirmed'))}) and removes UW-TIG\u2019s lead over the best classical rule, but UW-TIG still matches the strongest planners at a lower flight cost than R\u00fcckin\u2019s IPP "
  "and the coverage guarantee remains the decisive component. Fine-tuning the detector on two further public datasets raised its held-out dacl10k score from "
  f"{DET['old']['dacl']['map50']:.3f} to {DET['new']['dacl']['map50']:.3f} mAP50 but did not improve the closed loop, so it was not adopted.")
P("Equally important is what the measurements say about the work. The coverage guarantee, not the more elaborate terms, "
  "accounts for the large gain over the plain information-gain baseline; the uncertainty and growth terms do not yet change any reported number; much "
  "of the improvement over the first sweep came from correcting five flaws in how the system was <i>measured</i>; the "
  "uncertainty signal is poorly calibrated; and the growing-defect scenario fails because of the detector, not the memory. We "
  "report these because a planner that is only shown where it wins cannot be trusted where it matters.")
P("The simulation testbed is a result in its own right. It gives a controlled, repeatable setting \u2013 real defect imagery, a fixed "
  "viewpoint graph, leakage-free memory, a development/test split and a one-command sweep \u2013 in which any planner can be added "
  "to the registry and compared at the cost of a few CPU-hours, without a drone. We expect it to be the more reusable part of this work.")

# ================================================================ BIBLIOGRAPHY
story.append(SetHeader("Bibliography", ""))
story.append(PageBreak())
story.append(Paragraph("BIBLIOGRAPHY", S["chap"]))
refs = [
    "J. R\u00fcckin, L. Jin, F. Magistri, C. Stachniss and M. Popovi\u0107, \u201cAn informative path planning framework for active learning in UAV-based semantic mapping,\u201d <i>IEEE Trans. Robotics</i>, vol. 39, pp. 4279\u20134296, 2023, arXiv:2302.03347.",
    "A. Vashisth, J. R\u00fcckin, F. Magistri, C. Stachniss and M. Popovi\u0107, \u201cDeep reinforcement learning with dynamic graphs for adaptive informative path planning,\u201d arXiv:2402.04894, 2024.",
    "B. Moon, N. Suvarna, A. Jong, S. Chatterjee, J. Yuan, M. Cao and S. Scherer, \u201cIA-TIGRIS: An incremental and adaptive sampling-based planner for online informative path planning,\u201d <i>IEEE Trans. Robotics</i>, 2026, arXiv:2502.15961.",
    "K. Li, M. Mantovani, R. J. Wood, L. Sabattini and S. Gil, \u201cMotion-uncertainty-aware next-best-view planning for moving object reconstruction,\u201d in <i>Robotics: Science and Systems (RSS)</i>, 2026.",
    "L. Petit and A. Lussier Desbiens, \u201cMOAR Planner: Multi-objective and adaptive risk-aware path planning for infrastructure inspection with a UAV,\u201d in <i>Proc. ICRA</i>, 2024.",
    "S. Svystun, O. Melnychenko, P. Radiuk, O. Savenko, A. Sachenko and A. Lysyi, \u201cDynamic trajectory adaptation for efficient UAV inspections of wind energy units,\u201d arXiv:2411.17534, 2024.",
    "H. Jin, Z. Xu, H. Shen, X. Han, K. Ye and K. Shimada, \u201cAdaptive planning framework for UAV-based surface inspection in partially unknown indoor environments,\u201d arXiv:2504.09294, 2025.",
    "H. K. Dhami, F. Yu, K. Williams, S. Vajipey and P. Tokekar, \u201cGATSBI: An online GTSP-based algorithm for targeted surface bridge inspection,\u201d in <i>Proc. Int. Conf. Unmanned Aircraft Systems (ICUAS)</i>, 2023.",
    "H. K. Dhami, C. Reddy, V. D. Sharma, T. Williams and P. Tokekar, \u201cGATSBI: An online GTSP-based algorithm for targeted surface bridge inspection and defect detection,\u201d arXiv:2406.16625, 2024.",
    "H. K. Dhami, V. D. Sharma and P. Tokekar, \u201cPred-NBV: Prediction-guided next-best-view for 3D object reconstruction,\u201d in <i>Proc. IROS</i>, 2023, arXiv:2304.11465; and \u201cMAP-NBV: Multi-agent prediction-guided next-best-view planning for active 3D object reconstruction,\u201d arXiv:2307.04004, 2023.",
    "K. C. Teixeira Vivaldini, R. Pe\u0148i\u010dka and M. Saska, \u201cDecision-making-based path planning for autonomous UAVs: A survey,\u201d arXiv:2508.09304, 2025.",
    "A. F. Nikkhah, D. Chen, B. Campbell, S. Asadi and A. Heydarian, \u201cUAV-based infrastructure inspections: A literature review and proposed framework for AEC+FM,\u201d in <i>Int. Conf. Computing in Civil Engineering (i3CE)</i>, 2025, arXiv:2601.11665.",
    "Q. Zha, Y. Yao, Y. Zheng, W. Ma and W. Zhang, \u201cA dataset of building surface defects collected by UAVs for machine learning-based detection,\u201d <i>Scientific Data</i>, Nov. 2025 (MBDD2025; Zenodo 10.5281/zenodo.15622584).",
    "S. Huang, Q. Liu, C. Chen and Y. Chen, \u201cA real-time concrete crack detection and segmentation model based on YOLOv11,\u201d arXiv:2508.11517, 2025.",
    "Inam et al., YOLOv5-based bridge crack detection on field data and SDNET2018, 2023 (as reported by the authors; best of three variants).",
    "Li, Shi and Sun, improved YOLOv11 for utility-tunnel defect detection on a private dataset, 2026 (as reported by the authors).",
    "F. Shen, J. Cui, W. Li and S. Zhou, \u201cTinyDef-DETR: A transformer-based framework for defect detection in transmission lines from UAV imagery,\u201d arXiv:2509.06035, 2025.",
    "L. Hebbache, D. Amirkhani, M. S. Allili and J.-F. Lapointe, \u201cSaliency-guided deep learning for bridge defect detection in drone imagery,\u201d arXiv:2511.14040, 2025.",
    "S. Shah, D. Dey, C. Lovett and A. Kapoor, \u201cAirSim: High-fidelity visual and physical simulation for autonomous vehicles,\u201d in <i>Field and Service Robotics</i>, 2017.",
    "Y. Song, S. Naji, E. Kaufmann, A. Loquercio and D. Scaramuzza, \u201cFlightmare: A flexible quadrotor simulator,\u201d in <i>Conf. Robot Learning (CoRL)</i>, 2020.",
    "Y. Chen et al., GRaD-Nav (quadrotor navigation using 3-D Gaussian Splatting), 2025.",
    "J. Panerati, H. Zheng, S. Zhou, J. Xu, A. Prorok and A. P. Schoellig, \u201cLearning to fly \u2013 a gym environment with PyBullet physics for reinforcement learning of multi-agent quadcopter control,\u201d in <i>Proc. IROS</i>, 2021.",
    "S. Isler, R. Sabzevari, J. Delmerico and D. Scaramuzza, \u201cAn information gain formulation for active volumetric 3D reconstruction,\u201d in <i>Proc. IEEE Int. Conf. Robotics and Automation (ICRA)</i>, 2016.",
    "A. Bircher, M. Kamel, K. Alexis, H. Oleynikova and R. Siegwart, \u201cReceding horizon \u2018next-best-view\u2019 planner for 3D exploration,\u201d in <i>Proc. ICRA</i>, 2016, pp. 1462\u20131468.",
    "S. Alamdari, E. Fata and S. L. Smith, \u201cPersistent monitoring in discrete environments: Minimizing the maximum weighted latency between observations,\u201d <i>Int. J. Robotics Research</i>, vol. 33, no. 1, pp. 138\u2013154, 2014.",
    "H. Jin, Z. Xu, H. Shen, X. Han, K. Ye and K. Shimada, “ASIP-Planner: Adaptive planning for UAV surface inspection in partially known indoor environments,” in <i>Proc. IROS</i>, 2026, arXiv:2605.11119.",
    "C. Feng, Y. Xu and S. Shen, “FC-Vision: Real-time visibility-aware replanning for occlusion-free aerial target structure scanning in unknown environments,” <i>IEEE Robotics and Automation Letters</i>, 2026, arXiv:2602.13720.",
    "C. Li, H. He, X. Wang, W. Lin and C. H. Lim, “UnGAP: Uncertainty-guided affine prompting for real-time crack segmentation,” arXiv:2605.02380, 2026.",
    "J. Flotzinger, P. J. R\u00f6sch and T. Braml, “dacl10k: Benchmark for semantic bridge damage segmentation,” in <i>Proc. WACV</i>, 2024, arXiv:2309.00460.",
    "J. Flotzinger, F. Deuser, A. Jaziri, H. Neumann, N. Oswald, V. Ramesh and T. Braml, \u201csynth-dacl: Does synthetic defect data enhance segmentation accuracy and robustness for real-world bridge inspections?\u201d arXiv:2506.14255, 2025.",
    "F. Ciaglia, F. S. Zuppichini, P. Guerrie, M. McQuade and J. Solawetz, \u201cRoboflow 100: A rich, multi-domain object detection benchmark,\u201d arXiv:2211.13523, 2022.",
    "\u00c7. F. \u00d6zgenel and A. G. Sorgu\u00e7, \u201cPerformance comparison of pretrained convolutional neural networks on crack detection in buildings,\u201d in <i>Proc. Int. Symp. Automation and Robotics in Construction (ISARC)</i>, 2018.",
    "S. Dorafshan, R. J. Thomas and M. Maguire, \u201cSDNET2018: An annotated image dataset for non-contact concrete crack detection using deep convolutional neural networks,\u201d <i>Data in Brief</i>, vol. 21, pp. 1664\u20131668, 2018."
]
for i, r in enumerate(refs, 1):
    story.append(Paragraph(f"[{i}]&nbsp;&nbsp;{r}", S["ref"]))

# ================================================================ APPENDICES
def get_src(relpath, names):
    path = os.path.join(ROOT, relpath)
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    lines = src.splitlines()
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            out.append("\n".join(lines[node.lineno - 1: node.end_lineno]))
    return "\n\n".join(out)


def code(title, text):
    story.append(Paragraph(f"<b>{title}</b>", S["bodyni"]))
    chunk = []
    for ln in text.splitlines():
        chunk.append(ln.replace("\t", "    ")[:118])
        if len(chunk) >= 62:
            story.append(Preformatted("\n".join(chunk), S["code"]))
            chunk = []
    if chunk:
        story.append(Preformatted("\n".join(chunk), S["code"]))
    story.append(Spacer(1, 8))


story.append(SetHeader("Appendices", ""))
story.append(PageBreak())
story.append(Paragraph("APPENDICES", S["chap"]))
code("Appendix A - UW-TIG planner (planning/planners.py)", get_src("planning/planners.py", {"UWTIGPlanner"}))
code("Appendix B - Mission belief: information gain, uncertainty, growth, staleness (planning/planners.py)", get_src("planning/planners.py", {"MissionBelief"}))
code("Appendix C - Localisation onto a wall (geometry.py)", get_src("geometry.py", {"localize_on_wall", "wall_plane", "ray_plane_intersect"}))
code("Appendix D - Defect-memory matching rule, in-process port (memory/store_mem.py)", get_src("memory/store_mem.py", {"InMemoryStore"}))

doc.multiBuild(story)
import json
json.dump({"body": BODY_START["page"], "front": FRONT_START["page"]}, open(_CACHE, "w"))


def stamp_page_numbers(path):
    """Roman numerals from the acknowledgement page, arabic from chapter 1."""
    import pymupdf
    d = pymupdf.open(path)
    front = body = None
    for i in range(d.page_count):
        t = d[i].get_text()
        if front is None and t.lstrip().startswith("ACKNOWLEDGEMENT"):
            front = i
        if body is None and "1.  INTRODUCTION" in t.replace(" ", " ")[:120]:
            body = i
    for i in range(d.page_count):
        if i >= body:
            label = str(i - body + 1)
        elif i >= front:
            label = ROMAN[i - front + 1]
        else:
            continue
        pg = d[i]
        w = pymupdf.get_text_length(label, fontname="tiro", fontsize=11)
        pg.insert_text(((pg.rect.width - w) / 2, pg.rect.height - 1.4 * 28.35 - 4), label, fontname="tiro", fontsize=11)
    tmp = path + ".tmp"
    d.save(tmp, garbage=3, deflate=True)
    d.close()
    os.replace(tmp, path)


stamp_page_numbers(OUT_PATH)
print("wrote", OUT_PATH, "body starts on physical page", BODY_START["page"])
