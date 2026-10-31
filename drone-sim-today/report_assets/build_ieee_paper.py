# -*- coding: utf-8 -*-
"""Builds the two-column, IEEE-conference-style paper (UW-TIG_IEEE_Paper.pdf).
Numbers come from results/scaleup_summary.json and results/detector_extra.json;
citations are written as [@key] and numbered by order of first appearance.
Run from drone-sim-today/:  venv python report_assets/build_ieee_paper.py"""
import json
import os
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, FrameBreak, Image, KeepTogether, NextPageTemplate, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGS = os.path.join(HERE, "paper_figs")
OUT = os.path.join(ROOT, "UW-TIG_IEEE_Paper.pdf")
SC = json.load(open(os.path.join(ROOT, "results", "scaleup_summary.json")))
DET = json.load(open(os.path.join(ROOT, "results", "detector_extra.json")))

F = r"C:\Windows\Fonts"
for n, f in (("Times", "times.ttf"), ("Times-B", "timesbd.ttf"), ("Times-I", "timesi.ttf"), ("Times-BI", "timesbi.ttf")):
    pdfmetrics.registerFont(TTFont(n, os.path.join(F, f)))
pdfmetrics.registerFontFamily("Times", normal="Times", bold="Times-B", italic="Times-I", boldItalic="Times-BI")


def SP(set_, p, k):
    return SC[set_]["planners"][p][k]


def SD(set_, p):
    d = SC[set_]["uwtig_vs"][p]
    return d["mean_diff"], d["ci"][0], d["ci"][1], d["seeds_won"], d["n"]


f3 = lambda v: f"{v:.3f}"
f0 = lambda v: f"{v:.0f}"

# ------------------------------------------------------------------ references (key -> text)
REFS = {
    "ruckin": "J. R\u00fcckin, L. Jin, F. Magistri, C. Stachniss and M. Popovi\u0107, \u201cAn informative path planning framework for active learning in UAV-based semantic mapping,\u201d <i>IEEE Trans. Robot.</i>, vol. 39, pp. 4279\u20134296, 2023.",
    "moon": "B. Moon <i>et al.</i>, \u201cIA-TIGRIS: An incremental and adaptive sampling-based planner for online informative path planning,\u201d <i>IEEE Trans. Robot.</i>, 2026, arXiv:2502.15961.",
    "vashisth": "A. Vashisth, J. R\u00fcckin, F. Magistri, C. Stachniss and M. Popovi\u0107, \u201cDeep reinforcement learning with dynamic graphs for adaptive informative path planning,\u201d arXiv:2402.04894, 2024.",
    "gatsbi": "H. K. Dhami, C. Reddy, V. D. Sharma, T. Williams and P. Tokekar, \u201cGATSBI: An online GTSP-based algorithm for targeted surface bridge inspection and defect detection,\u201d arXiv:2406.16625, 2024.",
    "asip": "H. Jin, Z. Xu, H. Shen, X. Han, K. Ye and K. Shimada, \u201cASIP-Planner: Adaptive planning for UAV surface inspection in partially known indoor environments,\u201d in <i>Proc. IROS</i>, 2026, arXiv:2605.11119.",
    "fcv": "C. Feng, Y. Xu and S. Shen, \u201cFC-Vision: Real-time visibility-aware replanning for occlusion-free aerial target structure scanning in unknown environments,\u201d <i>IEEE Robot. Autom. Lett.</i>, 2026, arXiv:2602.13720.",
    "moar": "L. Petit and A. Lussier Desbiens, \u201cMOAR Planner: Multi-objective and adaptive risk-aware path planning for infrastructure inspection with a UAV,\u201d in <i>Proc. IEEE ICRA</i>, 2024.",
    "svystun": "S. Svystun <i>et al.</i>, \u201cDynamic trajectory adaptation for efficient UAV inspections of wind energy units,\u201d arXiv:2411.17534, 2024.",
    "prednbv": "H. K. Dhami, V. D. Sharma and P. Tokekar, \u201cPred-NBV: Prediction-guided next-best-view for 3D object reconstruction,\u201d in <i>Proc. IEEE/RSJ IROS</i>, 2023.",
    "isler": "S. Isler, R. Sabzevari, J. Delmerico and D. Scaramuzza, \u201cAn information gain formulation for active volumetric 3D reconstruction,\u201d in <i>Proc. IEEE ICRA</i>, 2016.",
    "bircher": "A. Bircher, M. Kamel, K. Alexis, H. Oleynikova and R. Siegwart, \u201cReceding horizon \u2018next-best-view\u2019 planner for 3D exploration,\u201d in <i>Proc. IEEE ICRA</i>, 2016, pp. 1462\u20131468.",
    "alamdari": "S. Alamdari, E. Fata and S. L. Smith, \u201cPersistent monitoring in discrete environments: Minimizing the maximum weighted latency between observations,\u201d <i>Int. J. Robot. Res.</i>, vol. 33, no. 1, pp. 138\u2013154, 2014.",
    "mbdd": "Q. Zha, Y. Yao, Y. Zheng, W. Ma and W. Zhang, \u201cA dataset of building surface defects collected by UAVs for machine learning-based detection,\u201d <i>Sci. Data</i>, 2025.",
    "dacl": "J. Flotzinger, P. J. R\u00f6sch and T. Braml, \u201cdacl10k: Benchmark for semantic bridge damage segmentation,\u201d in <i>Proc. IEEE/CVF WACV</i>, 2024.",
    "synth": "J. Flotzinger <i>et al.</i>, \u201csynth-dacl: Does synthetic defect data enhance segmentation accuracy and robustness for real-world bridge inspections?\u201d arXiv:2506.14255, 2025.",
    "rf100": "F. Ciaglia, F. S. Zuppichini, P. Guerrie, M. McQuade and J. Solawetz, \u201cRoboflow 100: A rich, multi-domain object detection benchmark,\u201d arXiv:2211.13523, 2022.",
    "huang": "S. Huang, Q. Liu, C. Chen and Y. Chen, \u201cA real-time concrete crack detection and segmentation model based on YOLOv11,\u201d arXiv:2508.11517, 2025.",
    "gpd": "J. Panerati, H. Zheng, S. Zhou, J. Xu, A. Prorok and A. P. Schoellig, \u201cLearning to fly \u2013 a gym environment with PyBullet physics for reinforcement learning of multi-agent quadcopter control,\u201d in <i>Proc. IEEE/RSJ IROS</i>, 2021.",
    "airsim": "S. Shah, D. Dey, C. Lovett and A. Kapoor, \u201cAirSim: High-fidelity visual and physical simulation for autonomous vehicles,\u201d in <i>Field and Service Robotics</i>, 2017.",
    "ungap": "C. Li, H. He, X. Wang, W. Lin and C. H. Lim, \u201cUnGAP: Uncertainty-guided affine prompting for real-time crack segmentation,\u201d arXiv:2605.02380, 2026.",
}
ORDER = []


def cite(m):
    keys = [k.strip().lstrip("@") for k in m.group(1).split(",")]
    nums = []
    for k in keys:
        assert k in REFS, k
        if k not in ORDER:
            ORDER.append(k)
        nums.append(ORDER.index(k) + 1)
    return "[" + ", ".join(str(n) for n in nums) + "]"


def C(t):
    return re.sub(r"\[@([a-z0-9,@ ]+)\]", cite, t)


# ------------------------------------------------------------------ styles
BASE = dict(fontName="Times", fontSize=9.2, leading=10.9, alignment=TA_JUSTIFY)
st = {
    "body": ParagraphStyle("body", firstLineIndent=0.35 * cm, spaceAfter=2.2, **BASE),
    "bodyni": ParagraphStyle("bodyni", spaceAfter=2.2, **BASE),
    "h1": ParagraphStyle("h1", fontName="Times", fontSize=9.2, leading=11, alignment=TA_CENTER, spaceBefore=6, spaceAfter=3, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="Times-I", fontSize=9.2, leading=11, alignment=TA_LEFT, spaceBefore=3, spaceAfter=2, keepWithNext=1),
    "cap": ParagraphStyle("cap", fontName="Times", fontSize=8, leading=9.4, alignment=TA_JUSTIFY, spaceBefore=1, spaceAfter=5),
    "tcap": ParagraphStyle("tcap", fontName="Times", fontSize=8, leading=9.4, alignment=TA_CENTER, spaceBefore=3, spaceAfter=2),
    "ref": ParagraphStyle("ref", fontName="Times", fontSize=8, leading=9.4, alignment=TA_JUSTIFY, leftIndent=0.62 * cm, firstLineIndent=-0.62 * cm, spaceAfter=1.4),
    "abs": ParagraphStyle("abs", fontName="Times-B", fontSize=9.2, leading=10.9, alignment=TA_JUSTIFY, spaceAfter=3),
    "title": ParagraphStyle("title", fontName="Times-B", fontSize=17, leading=20, alignment=TA_CENTER, spaceAfter=7),
    "au": ParagraphStyle("au", fontName="Times", fontSize=9.2, leading=10.8, alignment=TA_CENTER),
    "af": ParagraphStyle("af", fontName="Times-I", fontSize=8.3, leading=9.8, alignment=TA_CENTER),
}
story = []


def H1(num, t):
    story.append(Paragraph(f"{num}.&nbsp;&nbsp;{t.upper()}", st["h1"]))


def H2(letter, t):
    story.append(Paragraph(f"{letter}.&nbsp;&nbsp;{t}", st["h2"]))


def P(t, first=True):
    story.append(Paragraph(C(t), st["body" if first else "bodyni"]))


def FIG(name, width_cm, cap):
    story.append(KeepTogether([Image(os.path.join(FIGS, name), width=width_cm * cm, height=width_cm * cm * _ratio(name)),
                               Paragraph(C(cap), st["cap"])]))


def _ratio(name):
    from PIL import Image as PI
    w, h = PI.open(os.path.join(FIGS, name)).size
    return h / w


def TABLE(cap, header, rows, widths, bold_row=None, left=(0,)):
    data = [[Paragraph(f"<b>{h}</b>", ParagraphStyle("th", fontName="Times", fontSize=7.8, leading=9, alignment=TA_CENTER)) for h in header]]
    for r in rows:
        data.append([Paragraph(C(str(c)), ParagraphStyle("td", fontName="Times-B" if bold_row is not None and r is rows[bold_row] else "Times", fontSize=7.8, leading=9,
                                                      alignment=TA_LEFT if i in left else TA_CENTER)) for i, c in enumerate(r)])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black), ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
                           ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
                           ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
    story.append(KeepTogether([Paragraph(cap, st["tcap"]), t, Spacer(1, 4)]))


# ------------------------------------------------------------------ numbers used in the prose
UWs, RKs = ("small_old", "uwtig"), ("small_old", "ruckin_ipp")
flyless_small = round(100 * (1 - SP("small_old", "uwtig", "total_flight_dist_m") / SP("small_old", "ruckin_ipp", "total_flight_dist_m")))
flyless_large = round(100 * (1 - SP("large_old", "uwtig", "total_flight_dist_m") / SP("large_old", "ruckin_ipp", "total_flight_dist_m")))
dR = SD("large_old", "ruckin_ipp"); dA = SD("large_old", "alamdari_latency"); dG = SD("large_old", "gatsbi_gtsp"); dX = SD("large_old", "random")
o, n = DET["old"], DET["new"]

# ------------------------------------------------------------------ title block
TEAM = ["Akhil Ramalingam", "Anbuchandiran K", "Neelesh Padmanabh", "Saumiyaa Sri V L", "Sowndarya Elangi S", "Therdhana J P"]
AFF = "Dept. of CSE<br/>PSG College of Technology<br/>Coimbatore, India"


def au_cell(name, role=None):
    cell = [Paragraph(name, st["au"])]
    if role:
        cell.append(Paragraph(f"<i>{role}</i>", st["af"]))
    cell.append(Paragraph(AFF, st["af"]))
    return cell


top = [Paragraph("UW-TIG: Uncertainty-Weighted Temporal Information Gain for Closed-Loop Drone Defect Inspection, Evaluated in a Scalable Simulation Testbed", st["title"])]
names = TEAM
rows = [[au_cell(x) for x in names[i:i + 3]] for i in range(0, 6, 3)]
rows.append([au_cell("Ms. L. Karthika", "Guide"), au_cell("Dr. N. Gopika Rani", "Co-Guide"), ""])
at = Table(rows, colWidths=[5.6 * cm] * 3)
at.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
top.append(at)
top.append(Spacer(1, 5))
story.extend(top)
story.append(FrameBreak())

# ------------------------------------------------------------------ abstract
story.append(Paragraph(C(
    f"<i>Abstract</i>\u2014Most drone inspection planners choose where to look from geometry alone. Such a planner has no idea what a defect is, carries nothing over from one flight to the next, and does not return for a second look when a detection is shaky. We describe UW-TIG, a viewpoint planner that extends a cost-normalised information-gain score with five ideas: a coverage phase, detector uncertainty, a defect memory that survives between missions and tracks growth, a staleness bonus for neglected spots, and a two-step lookahead, and a simulation testbed built so that the planner can be run, compared and repeated without a physical drone. "
    f"In a nine-wall yard UW-TIG reaches precision {f3(SP('small_old','uwtig','precision_confirmed'))}, recall {f3(SP('small_old','uwtig','recall_confirmed'))} and F1 "
    f"{f3(SP('small_old','uwtig','f1_confirmed'))} on held-out seeds, level with the strongest of five re-implemented planners while flying {flyless_small}% less. "
    f"Growing the yard to 31 walls lowers every planner\u2019s score: UW-TIG reaches F1 {f3(SP('large_old','uwtig','f1_confirmed'))}, statistically level with two rivals and "
    f"ahead of an uncertainty-driven IPP rule with {flyless_large}% less flight. Ablations credit the coverage phase with the gain; switching the uncertainty and growth terms off moves no metric yet. Fine-tuning the detector on two more public datasets lifted its held-out dacl10k "
    f"mAP50 from {o['dacl']['map50']:.3f} to {n['dacl']['map50']:.3f} but did not help the closed loop. A synthetic oracle detector and a sweep of the uncertainty and growth weights from 0 to 20 confirm that those two terms change nothing in this simulator, and a like-for-like comparison of YOLOv8n, s and m shows the small model captures almost all of the size gain. We report these negative results alongside the positive ones."),
    st["abs"]))
story.append(Paragraph("<i>Index Terms</i>\u2014UAV inspection, next-best-view, informative path planning, defect detection, uncertainty, simulation.",
                       ParagraphStyle("kw", fontName="Times-BI", fontSize=9.2, leading=10.9, alignment=TA_JUSTIFY, spaceAfter=4)))

# ------------------------------------------------------------------ I. Introduction
H1("I", "Introduction")
P("Cracks, corrosion and leaks in buildings, towers and pipelines are found by people walking or flying a route and looking. Drones have made "
  "the looking cheaper, but the flying is usually still fixed: a pre-planned path, or a path that maximises how much surface is covered. "
  "What the camera sees does not change where the drone goes next.")
P("Recent planners do close this loop in part. Uncertainty-driven informative path planning chooses views that most reduce a model\u2019s own doubt "
  "[@ruckin, @moon, @vashisth]; inspection planners route a UAV over target surfaces and add a defect detector [@gatsbi, @asip, @fcv]. "
  "Two gaps remain. These systems plan within a single session, so a defect found last month is not tracked or compared this month; and "
  "they report results on one scene size, so it is unclear whether a planner that works on nine walls still works on thirty.")
P("We make three contributions. (1) <b>UW-TIG</b>, a planner that combines five ingredients in one score: a coverage phase, detector uncertainty, "
  "defect growth from persistent memory, staleness and a two-step lookahead. (2) A <b>reproducible simulation testbed</b> in which real defect "
  "photographs are the wall textures, with a nine-wall and a 31-wall yard, four scenarios and an evaluation protocol with separate development and "
  "test seeds. (3) An <b>evidence-first evaluation</b>: seven planners, six ablations, bootstrap intervals over seeds, ten seeds on the small yard, a second yard size, planner-only tests with a synthetic oracle detector, and a "
  "detector trained on extra data. Several of our own mechanisms turn out not to matter on the metrics we measure, and we say so.")

# ------------------------------------------------------------------ II. Related work
H1("II", "Related Work")
P("<b>Informative path planning.</b> R\u00fcckin <i>et al.</i> choose UAV paths that teach a semantic-mapping network the most, scoring views by the network\u2019s own epistemic uncertainty per unit of travel cost [@ruckin]. Moon <i>et al.</i> reuse earlier planning effort for fast online replanning [@moon], "
  "and Vashisth <i>et al.</i> learn the planner with reinforcement learning on dynamic graphs [@vashisth]. All three work over a generic belief "
  "map, not over defects with an identity and a history.")
P("<b>Inspection planning.</b> GATSBI routes a UAV over bridge surfaces with a travelling-salesman formulation and, in its later version, detects "
  "defects [@gatsbi]. ASIP-Planner and FC-Vision handle obstacles that were missing from the map when the scan was planned [@asip, @fcv]; MOAR "
  "adapts paths to weather and battery [@moar], and Svystun <i>et al.</i> adapt wind-turbine inspections to blade pitch [@svystun]. None of these "
  "revisits a defect across missions.")
P("<b>Classical building blocks.</b> Cost-normalised entropy gain [@isler], receding-horizon next-best-view [@bircher] and "
  "maximum-latency persistent monitoring [@alamdari] are the three older ideas we borrow; we re-implement all three as baselines.")
P("<b>Defect data.</b> MBDD2025 is a set of 14,471 drone photos of building surfaces labelled with five defect classes [@mbdd]. dacl10k collects real bridge-inspection "
  "photographs [@dacl], and its 2025 follow-up shows synthetic textures improve robustness [@synth]. Roboflow-100 is a public multi-domain detection benchmark [@rf100]. "
  "Recent YOLO crack detectors report strong scores on single-class data [@huang].")

# ------------------------------------------------------------------ III. Testbed
H1("III", "Simulation Testbed")
P("The testbed has five parts, drawn in Fig. 1: a planner, a simulated camera, a trained detector, a geometry step that turns a detection into a "
  "position on a known wall, and a defect memory. Physics and the camera come from gym-pybullet-drones [@gpd].")
FIG("loop.png", 8.4, "Fig. 1. The closed loop. The memory feeds uncertainty, growth and staleness back into the next planning step.")
P("<b>Yard.</b> The original yard has nine inspectable walls: two freestanding buildings and a panel on each of a pipe rack and a lattice tower. "
  "The large yard has 31 (Fig. 2): four more buildings and six more freestanding panels over roughly 34 m by 28 m. Walls are flat textured quads, so "
  "ray-casting a detection onto a wall is exact. A wall that carries a defect gets a real MBDD2025 photo as its texture, cut to the wall\u2019s own width-to-height ratio so the defect is not stretched.")
FIG("yard.png", 8.0, "Fig. 2. The 31-wall yard (blue) and its 186 candidate viewpoints at 1.3 m (red) and 2.2 m (orange) standoff.")
P("<b>Viewpoints and scenarios.</b> Each wall has six candidate viewpoints (two standoffs, three lateral offsets), 54 in the small yard and 186 in the large. "
  "Four scenarios place defects: static, uncertain (faint), multi-defect, and growing (a procedural defect whose size rises across missions). "
  "In the large yard the defect walls are drawn at random per seed. A mission is a fixed step budget (16 steps small, 50 large); each scenario runs three missions in a row so that memory persists.")
P("<b>Two ways to fly.</b> A fast kinematic mode teleports the camera to each viewpoint and is used for all statistics; a PID-flight mode with full "
  "quadrotor dynamics is used for demonstration videos. We chose PyBullet over Unity or Unreal because the camera stays framed on the wall under "
  "inspection, so a more photorealistic renderer would not change what the detector sees [@airsim].")

# ------------------------------------------------------------------ IV. Method
H1("IV", "The UW-TIG Planner")
P("At each step the planner scores every candidate viewpoint <i>v</i> and flies to the best one:")
story.append(Paragraph("U(v) = 1.0·IG(v) + 1.5·Unc(v) + 2.0·Gr(v) + 1.0·St(v) − 0.4·Cost(v)&nbsp;&nbsp;&nbsp;(1)",
                       ParagraphStyle("eq", fontName="Times-I", fontSize=8.1, leading=12, alignment=TA_CENTER, spaceBefore=2, spaceAfter=3)))
P("where IG, Unc, Gr and St are the information-gain, uncertainty, growth and staleness terms described next and Cost is the travel distance. The weights were set once on development seeds and not tuned afterwards.", first=False)
P("<b>Information gain</b> counts how much of the wall a viewpoint can still teach us. Walls are split into 1 m cells; a cell seen <i>n</i> times has "
  "belief 1 \u2212 0.5e<super>\u22120.6n</super> of being adequately observed, and IG(v) sums the entropy of the cells the viewpoint sees. "
  "<b>Uncertainty</b> is the spread of the detector\u2019s confidence over five copies of each frame (the original and four brightness, noise and blur variants); "
  "memory stores the last value per cell, and Unc(v) sums it, faded by the same e<super>\u22120.6n</super> so a spot does not pay out forever. "
  "<b>Growth</b> is the non-negative increase in a matched defect\u2019s physical size since the previous mission. <b>Staleness</b> is "
  "1 \u2212 e<super>\u22120.15t</super> per cell, with <i>t</i> the steps since the cell was last seen.")
P("<b>Coverage phase.</b> While any wall is still unvisited in the current mission, the planner considers only the viewpoints of unvisited walls and scores them "
  "with IG(v) \u2212 0.4 Cost(v) alone. It exists because a plain information-gain planner, and every early version of ours, stopped at four of nine walls on every seed. Under a cost-divided greedy rule the trip to the far building never pays for itself while nearby gain remains. No weight change fixed that; a separate phase did.")
P("<b>Lookahead.</b> Once every wall has been seen, a candidate v<sub>1</sub> is credited with its own utility plus half the best utility available from the view that would follow it. Only v<sub>1</sub> is flown; the planner then replans from there.")
P("<b>Perception and memory.</b> A YOLOv8s detector trained on MBDD2025 finds defects; each box centre is ray-cast onto the wall plane to get a 3-D position and "
  "physical size. A detection is matched to a stored defect if it has the same class and wall and lies within 0.35 m, using nearest neighbours of an "
  "appearance-and-position embedding; otherwise a new defect is created. A (wall, class) pair counts as <i>reported</i> once it has been seen three times (across missions) or once with confidence of at least 0.45; every planner is held to the same rule.")

# ------------------------------------------------------------------ V. Setup
H1("V", "Experimental Setup")
P("<b>Protocol.</b> Viewpoint standoffs, the reporting rule and all bug fixes were settled on development seeds 100\u2013102. Reported numbers come from a single run on test seeds 0\u20134. We report precision, recall and F1 of confirmed (wall, class) reports against ground truth, total flight distance, and coverage. "
  "Averages are over the static, uncertain and multi-defect scenarios; growing is excluded because the detector, trained on photographs, does not recognise "
  "its procedural defect. Error bars are 95% bootstrap intervals that resample the five seeds (each the mean over its scenarios) because rows from one seed are correlated.")
P("<b>Baselines.</b> Seven planners share the viewpoint graph, belief and reporting rule: random choice; Isler-style cost-normalised entropy gain [@isler]; "
  "Bircher-style depth-two receding horizon [@bircher]; Alamdari-style greedy maximum-latency [@alamdari]; a GATSBI-style tour over least-inspected walls [@gatsbi]; "
  "an R\u00fcckin-style acquisition of uncertainty over visit count [@ruckin]; and UW-TIG. Each is our reading of the cited paper\u2019s <i>view-selection rule</i> only; we do not reproduce the authors\u2019 full systems or quote their published figures.")
P("<b>Detector data.</b> Table I lists the datasets. MBDD2025\u2019s train/validation/test split is unchanged throughout. For the extra-data study, the same weights "
  "were fine-tuned for 30 epochs on MBDD2025 plus dacl10k and a Roboflow corrosion set, after mapping dacl10k labels onto our five classes (wet spot and efflorescence became leakage, spalling became abscission, rust became corrosion, both crack types became crack). dacl10k\u2019s own validation split stays held out. SDNET2018 was our first choice, but every mirror we tried sat behind a bot check.")
TABLE("TABLE I. Datasets used.", ["Dataset", "Role", "Images"], [
    ["MBDD2025 [@mbdd]", "Train, val, test; wall textures", "10,129 / 2,894 / 1,448"],
    ["dacl10k [@dacl]", "Fine-tune; held-out test", "5,362 + 466; 810"],
    ["Roboflow corrosion [@rf100]", "Fine-tune", "851"],
    ["Concrete-crack crops", "Crack-presence check only", "400 + 400"],
], [3.2, 3.3, 2.1], left=(0, 1, 2))
story[-1]  # (kept for clarity)

# ------------------------------------------------------------------ VI. Results
H1("VI", "Results")
H2("A", "Nine-wall yard")
rows = []
for p, nm in [("uwtig", "UW-TIG"), ("ruckin_ipp", "R\u00fcckin-style"), ("alamdari_latency", "Alamdari-style"), ("gatsbi_gtsp", "GATSBI-style"),
              ("random", "Random"), ("bircher_rhnbv", "Bircher-style"), ("isler_nbv", "Isler-style")]:
    rows.append([nm, f3(SP("small_old", p, "precision_confirmed")), f3(SP("small_old", p, "recall_confirmed")), f3(SP("small_old", p, "f1_confirmed")),
                 f0(SP("small_old", p, "total_flight_dist_m")), f"{SP('small_old', p, 'coverage_frac'):.2f}"])
TABLE("TABLE II. Nine-wall yard, test seeds 0\u20134 (confirmed reports; flight over three missions).", ["Planner", "Prec.", "Recall", "F1", "Flight (m)", "Cov."],
      rows, [2.6, 1.2, 1.2, 1.2, 1.4, 1.0], bold_row=0)
P(f"On detection quality UW-TIG is level with the best rival (F1 {f3(SP('small_old','uwtig','f1_confirmed'))} against {f3(SP('small_old','ruckin_ipp','f1_confirmed'))} for the "
  f"R\u00fcckin-style rule, with per-seed F1 for UW-TIG ranging from 0.890 to 1.000) and flies {f0(SP('small_old','uwtig','total_flight_dist_m'))} m against "
  f"{f0(SP('small_old','ruckin_ipp','total_flight_dist_m'))} m. Its localisation error is the lowest of the seven. The planners without a coverage mechanism fail "
  f"on coverage, not on detection: Isler-style and Bircher-style reach only {SP('small_old','isler_nbv','coverage_frac'):.2f} and {SP('small_old','bircher_rhnbv','coverage_frac'):.2f} of the walls.")
H2("B", "Ablations")
rows = []
for p, nm in [("uwtig", "Full UW-TIG"), ("uwtig_no_uncertainty", "No uncertainty"), ("uwtig_no_temporal", "No growth"), ("uwtig_no_staleness", "No staleness"),
              ("uwtig_no_lookahead", "No lookahead"), ("uwtig_no_coverage_first", "No coverage phase")]:
    rows.append([nm, f3(SP("small_old", p, "f1_confirmed")), f0(SP("small_old", p, "total_flight_dist_m")),
                 f3(SP("large_old", p, "f1_confirmed")), f0(SP("large_old", p, "total_flight_dist_m"))])
TABLE("TABLE III. Ablations: F1 and flight (m) in both yards.", ["Variant", "F1 (9)", "Flight (9)", "F1 (31)", "Flight (31)"], rows, [2.8, 1.3, 1.5, 1.3, 1.6], bold_row=0)
P("Only the coverage phase matters: without it recall falls and coverage drops to 0.44 (nine walls) and 0.52 (31 walls). Dropping the uncertainty or growth term shifts F1 by less than 0.005 and the route by under a metre. Dropping staleness or lookahead gives a shorter route at the same F1. The uncertainty and growth terms are inactive "
  "for two reasons we could check: the coverage phase ignores them, and the scored scenarios contain no real growth, so the growth score is noise clipped at zero. Section VI-E tests both explanations directly.")
H2("C", "A 31-wall yard")
rows = []
for p, nm in [("uwtig", "UW-TIG"), ("alamdari_latency", "Alamdari-style"), ("gatsbi_gtsp", "GATSBI-style"), ("ruckin_ipp", "R\u00fcckin-style"),
              ("random", "Random"), ("bircher_rhnbv", "Bircher-style"), ("isler_nbv", "Isler-style")]:
    ci = SP("large_old", p, "f1_ci")
    rows.append([nm, f3(SP("large_old", p, "f1_confirmed")), f"{ci[0]:.3f}\u2013{ci[1]:.3f}", f0(SP("large_old", p, "total_flight_dist_m")),
                 f"{SP('large_old', p, 'coverage_frac'):.2f}"])
TABLE("TABLE IV. 31-wall yard, budget 50 (F1 with 95% bootstrap interval over seeds).", ["Planner", "F1", "95% CI", "Flight (m)", "Cov."], rows,
      [2.6, 1.2, 2.2, 1.5, 1.0], bold_row=0)
FIG("scatter.png", 8.3, "Fig. 3. F1 against flight distance in the 31-wall yard (bars: 95% bootstrap interval over seeds).")
P(f"Every planner that reaches full coverage loses F1 relative to the small yard; UW-TIG goes from {f3(SP('small_old','uwtig','f1_confirmed'))} to "
  f"{f3(SP('large_old','uwtig','f1_confirmed'))}. Paired per-seed differences show UW-TIG level with the Alamdari-style rule ({dA[0]:+.3f}, interval {dA[1]:+.3f} to {dA[2]:+.3f}) "
  f"and the GATSBI-style tour ({dG[0]:+.3f}, {dG[1]:+.3f} to {dG[2]:+.3f}), ahead of the R\u00fcckin-style rule by {dR[0]:+.3f} (interval {dR[1]:+.3f} to {dR[2]:+.3f}, "
  f"excluding zero, {dR[3]} of {dR[4]} seeds) and far ahead of random search ({dX[0]:+.3f}). What UW-TIG keeps is cost: "
  f"{f0(SP('large_old','uwtig','total_flight_dist_m'))} m against {f0(SP('large_old','ruckin_ipp','total_flight_dist_m'))} m for the R\u00fcckin-style rule. "
  "So at this scale UW-TIG equals the best detection scores for less flying; it does not beat every rival.")
H2("D", "Training the detector on more data")
TABLE("TABLE V. Detector before and after fine-tuning (mAP50, precision/recall).", ["Test set", "Original", "Fine-tuned"], [
    ["MBDD2025 test (1,448)", f"{o['mbdd']['map50']:.3f}", f"{n['mbdd']['map50']:.3f}"],
    ["dacl10k held-out (810)", f"{o['dacl']['map50']:.3f}", f"{n['dacl']['map50']:.3f}"],
    ["dacl10k precision / recall", f"{o['dacl']['p']:.3f} / {o['dacl']['r']:.3f}", f"{n['dacl']['p']:.3f} / {n['dacl']['r']:.3f}"],
    ["Crack presence, recall (800 crops)", f"{o['crack_presence']['recall']:.3f}", f"{n['crack_presence']['recall']:.3f}"],
], [4.3, 2.1, 2.1], left=(0,))
P(f"Fine-tuning leaves the original test set unchanged ({o['mbdd']['map50']:.3f} to {n['mbdd']['map50']:.3f}) and lifts held-out dacl10k from "
  f"{o['dacl']['map50']:.3f} to {n['dacl']['map50']:.3f}, which is still a modest score, since dacl10k is difficult and our class mapping is a judgement call. "
  "The concrete-crack check fails for both detectors; those 227-pixel close-ups are far from anything either model was trained on, so we read it as a limit of the "
  "check, not as evidence about cracks in general.")
P(f"The extra data did not help the planner. With the fine-tuned detector UW-TIG\u2019s F1 is {f3(SP('small_new','uwtig','f1_confirmed'))} in the nine-wall yard "
  f"(against {f3(SP('small_old','uwtig','f1_confirmed'))}) and {f3(SP('large_new','uwtig','f1_confirmed'))} in the 31-wall yard (against {f3(SP('large_old','uwtig','f1_confirmed'))}). "
  "The simulator\u2019s textures are MBDD2025 photographs, so dacl10k\u2019s gain cannot show up in the loop, and fine-tuning may also have shifted the confidence "
  "calibration that the reporting rule was tuned on. We did not separate the two explanations and kept the original detector as the default.")

H2("E", "Planner-only tests: oracle detector, weights and ten seeds")
P("Two explanations remain for the null result on uncertainty and growth: the real detector gives too weak a signal, or the terms are too weak at their weights (1.5 and 2.0). "
  "We tested both. An <b>oracle detector</b> reads the scenario’s ground truth and returns detections with controlled noise (15% misses, confidence rising with severity, "
  "faint defects more uncertain, defects that genuinely grow); it is a synthetic planner-only test and says nothing about real detection quality.")
TABLE("TABLE VI. Oracle detector, 31-wall yard (static, uncertain, multi-defect; five seeds).", ["Variant", "F1", "Flight (m)"], [
    ["Full UW-TIG", "0.871", "480"], ["No uncertainty", "0.870", "480"], ["No growth", "0.871", "480"],
    ["No staleness", "0.862", "407"], ["No lookahead", "0.864", "445"], ["No coverage phase", "0.613", "174"],
], [3.6, 2.0, 2.4], bold_row=0)
P("With clean signals the no-uncertainty and no-growth variants still fly the identical route, and in the growing scenario every variant, including the one without the growth term, "
  "detects the growth (fraction 1.0), because the coverage and revisit logic already finds it. Raising both weights to 0, 6 and 20 leaves F1 unchanged (nine walls 0.918 in all three; "
  "31 walls 0.822, 0.821, 0.820). Staleness and lookahead shorten the flight (nine walls 81–83 m against 125 m) with no loss of real-detector F1 (Section VI-E, ten seeds), but cost a little oracle F1; here they add "
  "efficiency, not detection quality.")
P("<b>Ten seeds.</b> Extending both yards to seeds 0–9 with the original detector (confirmed F1, 95% bootstrap interval over seeds) gives, in the nine-wall yard, UW-TIG 0.963 (0.941–0.982) at 125 m, "
  "Alamdari-style 0.951 at 168 m, Rückin-style 0.938 at 206 m, GATSBI-style 0.914, random 0.891, Bircher-style 0.816 and Isler-style 0.663. UW-TIG’s paired lead is +0.012 over the Alamdari-style rule "
  "(+0.001 to +0.022, 6 of 10 seeds) and +0.025 over the Rückin-style rule (−0.002 to +0.055): small, and not significant over Rückin. In the 31-wall yard the order is Alamdari-style 0.928 (570 m), "
  "UW-TIG 0.921 (481 m), GATSBI-style 0.917 (471 m), Rückin-style 0.906 (846 m): UW-TIG is level with the first two and ahead of the Rückin-style rule by +0.014 (+0.001 to +0.029) with 43% less flight. "
  "In both yards the no-uncertainty and no-growth variants stay within 0.002 of UW-TIG. Removing staleness or lookahead raises nine-wall F1 to 0.973 (paired +0.010, +0.003 to +0.017) and cuts flight to 81–83 m, "
  "and ties at 31 walls, so those two terms cost flight and, in the small yard, a little detection quality.")
H2("F", "Detector size")
P("Earlier detector rows differ in resolution and epochs, so we retrained YOLOv8n, s and m with one recipe (a fixed 4,000-image MBDD2025 subset, 640 px, 30 epochs, seed 0) and scored them on the full test split.")
TABLE("TABLE VII. YOLOv8 size comparison under identical training (one run each).", ["Model", "Params (M)", "mAP50", "mAP50-95"], [
    ["YOLOv8n", "3.0", "0.743", "0.373"], ["YOLOv8s", "11.1", "0.793", "0.411"], ["YOLOv8m", "25.8", "0.796", "0.418"],
], [2.4, 2.0, 1.8, 2.0], left=(0,))
P("Moving from n to s gains 0.050 mAP50; moving from s to m gains 0.003, within run-to-run noise, for 2.3 times the parameters. We therefore keep the small model. "
  "These subset scores are below the default detector’s 0.884, which saw all 12,955 training images for 100 epochs.")

# ------------------------------------------------------------------ VII. Discussion
H1("VII", "Discussion and Limitations")
P("The honest summary is that UW-TIG\u2019s measured contribution is a coverage guarantee plus a cost-aware utility that is competitive with the best rule we "
  "re-implemented. Uncertainty and growth, the two ideas the planner is named for, are not visible in any number, even with a clean synthetic detector and weights up to twenty times larger (Section VI-E); we report them as untested extensions. The detector\u2019s confidence is also poorly "
  "calibrated (expected calibration error 0.29\u20130.33, and mean uncertainty is slightly <i>lower</i> on wrong detections), so it is used only to rank views. "
  "Recent work on uncertainty-guided crack models suggests better uncertainty is possible [@ungap].")
P("Limits: the baselines are re-implemented selection rules, not full systems; five seeds (ten on the nine-wall yard); the same reporting rule and a budget picked from a single pilot are used in the large yard; "
  "the 31-wall sweeps ran on an in-process re-write of the defect memory that we never compared with the database version on the same runs; walls are flat quads rendered by a software "
  "rasteriser with no wind or sensor noise; and because MBDD2025 holds no growth sequences, all temporal behaviour is tested on one procedural scenario that the detector fails to see.")

# ------------------------------------------------------------------ VIII. Conclusion
H1("VIII", "Conclusion")
P("We built a closed-loop inspection planner and a simulation testbed to measure it. UW-TIG matches the strongest re-implemented planners on detection in a nine-wall and a "
  "31-wall yard at lower flight cost, and its coverage phase is necessary. Scaling the yard and training on more data both gave humbler results than the first headline, "
  "which is the reason for running them. Next we plan to texture the simulator with dacl10k-style imagery, re-tune the reporting rule for the broader detector, and add "
  "scenarios with real growth so that the uncertainty and growth terms can be tested.")
story.append(Paragraph("ACKNOWLEDGMENT", st["h1"]))
P("The authors thank the Department of Computer Science and Engineering, PSG College of Technology, for its support. The code, results and figures are in the project repository.", first=True)

# ------------------------------------------------------------------ references (built last so numbering is final)
story.append(Paragraph("REFERENCES", st["h1"]))
for i, k in enumerate(ORDER, 1):
    story.append(Paragraph(f"[{i}]&nbsp;&nbsp;{REFS[k]}", st["ref"]))


# ------------------------------------------------------------------ document
def build():
    W, H = A4
    lm, rm, tm, bm, gap = 1.6 * cm, 1.6 * cm, 1.7 * cm, 1.8 * cm, 0.6 * cm
    cw = (W - lm - rm - gap) / 2
    top_h = 7.9 * cm
    first = PageTemplate("first", frames=[
        Frame(lm, H - tm - top_h, W - lm - rm, top_h, id="top", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        Frame(lm, bm, cw, H - tm - top_h - bm, id="c1", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        Frame(lm + cw + gap, bm, cw, H - tm - top_h - bm, id="c2", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
        autoNextPageTemplate="later")
    later = PageTemplate("later", frames=[
        Frame(lm, bm, cw, H - tm - bm, id="c1", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0),
        Frame(lm + cw + gap, bm, cw, H - tm - bm, id="c2", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)])
    doc = BaseDocTemplate(OUT, pagesize=A4, pageTemplates=[first, later], title="UW-TIG: Uncertainty-Weighted Temporal Information Gain",
                          author="A. Ramalingam, Anbuchandiran K, N. Padmanabh, S. S. V L, S. Elangi S, T. J P")
    doc.build(story)
    print("wrote", OUT, "refs:", len(ORDER))


build()
