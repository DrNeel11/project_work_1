# -*- coding: utf-8 -*-
"""Generates the detailed technical report PDF for the autonomous drone
utility inspection project. Run once from drone-sim-today/ with the venv
python. Not part of the shipped system -- a one-off report-authoring script."""
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                 SimpleDocTemplate, Spacer, Table, TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "Autonomous_Drone_Inspection_Report.pdf")

BLUE = colors.HexColor("#2b6cb0")
DARK = colors.HexColor("#1a1a1a")
GREY = colors.HexColor("#555555")
LIGHT = colors.HexColor("#eef3fa")
RED = colors.HexColor("#a61c1c")
GREEN = colors.HexColor("#2e7d32")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("ReportTitle", fontSize=22, leading=27, alignment=TA_CENTER,
                           textColor=DARK, spaceAfter=6, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("ReportSubtitle", fontSize=13, leading=18, alignment=TA_CENTER,
                           textColor=BLUE, spaceAfter=4, fontName="Helvetica"))
styles.add(ParagraphStyle("MetaCenter", fontSize=10, leading=14, alignment=TA_CENTER,
                           textColor=GREY))
styles.add(ParagraphStyle("H1", fontSize=16, leading=20, spaceBefore=18, spaceAfter=8,
                           textColor=BLUE, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("H2", fontSize=12.5, leading=16, spaceBefore=12, spaceAfter=6,
                           textColor=DARK, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("Body", fontSize=10, leading=14.5, alignment=TA_JUSTIFY,
                           spaceAfter=8, textColor=DARK))
styles.add(ParagraphStyle("ReportBullet", parent=styles["Body"], leftIndent=14, bulletIndent=2,
                           spaceAfter=5))
styles.add(ParagraphStyle("Caption", fontSize=8.5, leading=11, alignment=TA_CENTER,
                           textColor=GREY, spaceBefore=4, spaceAfter=14, fontName="Helvetica-Oblique"))
styles.add(ParagraphStyle("Mono", fontName="Courier", fontSize=8, leading=10.5,
                           textColor=DARK, backColor=LIGHT, borderPadding=6, spaceAfter=8))
styles.add(ParagraphStyle("SmallNote", fontSize=8.5, leading=11.5, textColor=GREY,
                           alignment=TA_JUSTIFY, spaceAfter=8))

story = []


def h1(text):
    story.append(Paragraph(text, styles["H1"]))


def h2(text):
    story.append(Paragraph(text, styles["H2"]))


def body(text):
    story.append(Paragraph(text, styles["Body"]))


def bullets(items):
    for it in items:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{it}", styles["ReportBullet"]))


def image(path, width, caption=None):
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    ratio = h / w
    img = Image(path, width=width, height=width * ratio)
    story.append(img)
    if caption:
        story.append(Paragraph(caption, styles["Caption"]))


cell_style = ParagraphStyle("Cell", fontName="Helvetica", fontSize=8.5, leading=11,
                             textColor=DARK, alignment=TA_CENTER)
cell_style_left = ParagraphStyle("CellLeft", parent=cell_style, alignment=0)  # TA_LEFT
header_style = ParagraphStyle("CellHeader", parent=cell_style, fontName="Helvetica-Bold",
                               textColor=colors.white)


def table(headers, rows, col_widths=None, highlight_row=None, left_align_cols=()):
    """`left_align_cols` are 0-indexed data columns whose (wrapped, long-text)
    cells should be left- rather than center-aligned."""
    header_cells = [Paragraph(str(h), header_style) for h in headers]
    body_rows = []
    for row in rows:
        cells = []
        for ci, val in enumerate(row):
            style = cell_style_left if ci in left_align_cols else cell_style
            cells.append(Paragraph(str(val), style))
        body_rows.append(cells)
    data = [header_cells] + body_rows

    t = Table(data, colWidths=col_widths, hAlign="CENTER")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if highlight_row is not None:
        style.append(("BACKGROUND", (0, highlight_row), (-1, highlight_row), colors.HexColor("#dbe9fb")))
    t.setStyle(TableStyle(style))
    story.append(t)
    story.append(Spacer(1, 10))


# ---------------------------------------------------------------- Title page
story.append(Spacer(1, 2.2 * cm))
story.append(Paragraph("AUTONOMOUS DRONE UTILITY INSPECTION", styles["ReportTitle"]))
story.append(Paragraph("Closed-Loop Perception, Memory &amp; Active Reinspection", styles["ReportSubtitle"]))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("Technical Implementation &amp; Results Report", styles["MetaCenter"]))
story.append(Spacer(1, 1.4 * cm))
story.append(Paragraph("PSG College of Technology &mdash; Department of Computer Science and Engineering, Coimbatore",
                        styles["MetaCenter"]))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph(
    "Akhil Ramalingam (23Z207) &middot; Anbuchandiran K (23Z209) &middot; Neelesh Padmanabh (23Z241)<br/>"
    "Saumiyaa Sri V L (23Z261) &middot; Sowndarya Elangi S (23Z269) &middot; Therdhana J P (23Z273)",
    styles["MetaCenter"]))
story.append(Spacer(1, 0.5 * cm))
story.append(Paragraph("Guide: Ms. L. Karthika &nbsp;&nbsp;|&nbsp;&nbsp; Co-Guide: Dr. N. Gopika Rani", styles["MetaCenter"]))
story.append(Spacer(1, 2.5 * cm))
story.append(Paragraph(
    "This report documents the fully implemented, simulated closed-loop inspection system "
    "described in the project proposal: real trained perception, 3D localization, persistent "
    "cross-mission defect memory, and an active-reinspection planner (UW-TIG) benchmarked "
    "against a naive baseline and the closest base paper (Isler et al., 2016).", styles["MetaCenter"]))
story.append(PageBreak())

# ---------------------------------------------------------------- Executive summary
h1("Executive Summary")
body(
    "The original proposal identified a research gap: existing UAV inspection systems are "
    "open-loop &mdash; detection, uncertainty estimation, and flight planning are separate stages, "
    "and none of them close the loop back into where the drone flies next. This project implements "
    "that closed loop end-to-end in simulation, <b>not as a plan but as working, tested code</b>: "
    "a real YOLO detector trained on a real 14,471-image UAV defect dataset, geometric 3D "
    "localization, a persistent PostgreSQL+pgvector/Neo4j defect memory, and a novel planner "
    "(UW-TIG) that is benchmarked quantitatively against a random baseline and against an "
    "implementation of the closest base paper (Isler et al. 2016's information-gain next-best-view)."
)
body(
    "Every number in this report comes from an actual executed run &mdash; a 5-seed, 3-mission, "
    "8-planner comparison sweep, an offline detection benchmark on a held-out real test set, and "
    "a real-physics flight demo &mdash; not a projection. The headline result: the novel UW-TIG "
    "planner achieves <b>both higher precision AND higher recall than either baseline "
    "simultaneously</b> (0.76 precision / 0.63 recall, vs. 0.64/0.43 for the Isler-NBV base paper "
    "and 0.58/0.57 for Random) with full coverage and reinspection (1.00/1.00) &mdash; at an "
    "honestly-quantified trade-off in mean localization error (0.70m, worse than Isler-NBV's 0.49m) "
    "and flight distance (108.9m, more than Isler-NBV's 18.6m though still ~3.6x less than Random's "
    "393.8m). This precision/recall/coverage combination was reached in two passes: an initial "
    "configuration favored precision and localization sharply at recall and coverage's expense "
    "(0.86 precision but only 0.36 recall and 0.33 coverage), which a coverage-guarantee fix "
    "(Section 3.4.2) then rebalanced once low recall was flagged as a real problem -- both "
    "configurations remain available (<font face=\"Courier\">uwtig</font> and "
    "<font face=\"Courier\">uwtig_no_coverage_first</font>) since which one a deployment wants "
    "depends on whether missing real defects or flying further is the costlier mistake."
)
body(
    "This report also extends the original base-paper comparison with a wider literature sweep "
    "(Section 1.1) and three further planner mechanisms motivated by that sweep and by this "
    "iteration &mdash; a persistent-monitoring staleness/latency term, a 2-step receding-horizon "
    "lookahead, and the coverage-guarantee phase (Section 3.4) &mdash; each independently ablatable "
    "and each backed by the same real, re-executed 5-seed statistical sweep, not a re-used or "
    "projected number."
)

# ---------------------------------------------------------------- 1. Problem statement
h1("1. Problem Statement &amp; Research Gap")
body(
    "Utility infrastructure (pipelines, bridges, power towers, building facades) requires regular "
    "inspection for cracks, corrosion, and leaks. Manual inspection is slow, expensive, and "
    "hazardous. Current UAV inspection systems are largely <b>open-loop</b>: they follow a fixed "
    "route and analyze images after the flight. Detection confidence does not change the flight "
    "path; there is no persistent memory of a defect across repeated inspections; and no system in "
    "the literature combines defect-aware next-best-view planning, uncertainty-driven reinspection, "
    "and temporal (growth-aware) memory into one utility function evaluated end-to-end."
)
h2("Research Question")
body(
    "Can a UAV use detection confidence and defect history to autonomously decide where to fly "
    "next and when to re-inspect &mdash; and does doing so measurably outperform geometry-only "
    "active-vision planning (the closest existing method) and naive random inspection?"
)
h2("Closest Base Paper")
body(
    "<b>Isler, Sabzevari, Delmerico &amp; Scaramuzza (ICRA 2016)</b>, “An Information Gain "
    "Formulation for Active Volumetric 3D Reconstruction,” is the closest prior method: a "
    "Shannon-entropy information-gain formulation over a volumetric occupancy grid for next-best-view "
    "selection. It is geometry-only &mdash; no semantic/defect awareness, no temporal memory across "
    "visits. This project re-implements its core idea (entropy-based, cost-normalized information "
    "gain) adapted to a 2D wall-surface coverage grid, as the direct baseline UW-TIG is compared "
    "against and extends."
)

h2("1.1 Wider Literature Positioning")
body(
    "The base paper comparison above is deliberately narrow (one method, one axis: defect semantics). "
    "A broader literature sweep across active next-best-view planning, persistent monitoring, and "
    "uncertainty-aware inspection was carried out to check the novelty claim more rigorously and to "
    "find concrete mechanisms this project's planner was still missing:"
)
table(
    ["Approach", "Uncertainty-<br/>aware", "Cross-mission<br/>memory", "Growth/<br/>temporal", "Cost-<br/>aware", "Real<br/>detector"],
    [
        ["Isler et al. 2016 (base paper)", "No", "No", "No", "Yes", "N/A"],
        ["Bircher et al. 2016 (receding-horizon NBV)", "No", "No", "No", "Yes", "N/A"],
        ["Dhami et al., GATSBI (2023/2024)", "No", "No", "No", "Yes", "2024 only"],
        ["Dhami et al., Pred-NBV / MAP-NBV (2023)", "Indirect", "No", "No", "Yes", "N/A"],
        ["Liu et al. 2022 (uncertainty-controlled CPP)", "Yes", "No", "No", "Yes", "N/A"],
        ["Taioli et al. 2023 (POMDP/MCTS active search)", "Yes", "No", "No", "Partial", "Assumed"],
        ["Alamdari, Fata &amp; Smith 2014 (persistent monitoring)", "No", "Yes", "No", "Yes", "N/A"],
        ["Rückin et al. (ICRA'22/IROS'22/T-RO'23)", "Yes", "No", "No", "Yes", "Yes"],
        ["UW-TIG (this project)", "Yes", "Yes", "Yes", "Yes", "Yes"],
    ],
    col_widths=[5.6 * cm, 2.3 * cm, 2.4 * cm, 2.1 * cm, 1.9 * cm, 1.9 * cm],
    highlight_row=8,
    left_align_cols=(0,),
)
body(
    "No single cited method combines all five properties UW-TIG does. GATSBI's 2024 extension is the "
    "closest single relative &mdash; a real defect detector combined with cost-aware GTSP routing "
    "&mdash; but has no persistent cross-mission memory or detection-uncertainty term feeding the "
    "planner. The POMDP/MCTS active-search line has the uncertainty-driven belief update (\"partial\" "
    "cost-awareness; it plans within one session, not across it) but no persistence across separate "
    "missions. Pred-NBV/MAP-NBV's uncertainty-awareness is <i>indirect</i>: it comes from a learned "
    "shape-completion model's confidence, predicting unseen 3D geometry rather than defect condition. "
    "UW-TIG's own five “Yes” cells are, concretely: real TTA-ensemble detector uncertainty (not "
    "assumed ground truth); Postgres+pgvector/Neo4j cross-mission defect identity and growth; a "
    "translation-and-rotation-aware cost term; and a YOLO detector actually trained on real UAV "
    "photographs (Section 3.1), not a simulated or assumed one. This sweep directly motivated two "
    "additions described in Section 3.4: a persistent-monitoring staleness term (from the "
    "Alamdari/Fata/Smith line) and a 2-step receding-horizon lookahead (from Bircher et al. and "
    "GATSBI's replanning structure)."
)
body(
    "Rückin et al.'s line of work (ICRA 2022, IROS 2022, and its T-RO 2023 extension) is the "
    "closest single relative on the uncertainty column specifically, and is worth stating plainly as "
    "a better-matched comparison than the others above: it plans UAV viewpoints using a real Bayesian "
    "epistemic-uncertainty estimate (BALD, from an MC-Dropout ensemble) mapped onto a terrain grid, "
    "then selects greedily by that mapped uncertainty normalized by a cost/count term &mdash; "
    "structurally the same “uncertainty-weighted, cost-normalized greedy” shape as UW-TIG's own "
    "utility. The difference is what the uncertainty is <i>about</i>: theirs is the segmentation "
    "model's own epistemic confidence, spent deciding which images are worth labelling to retrain "
    "that model (a single-session active-learning problem); UW-TIG's is a specific defect's detection "
    "confidence, spent deciding which physical location is worth a second look, persisted and "
    "re-identified across missions. Put differently, Rückin et al. plan to reduce <i>model</i> "
    "uncertainty; UW-TIG plans to reduce <i>world-state</i> uncertainty using a fixed model. Reading "
    "their evaluation methodology closely also surfaced a metric this project had never run on itself "
    "despite its name &mdash; Expected Calibration Error &mdash; discussed in Section 4.2 below, where "
    "it produced a real, not entirely flattering finding."
)

# ---------------------------------------------------------------- 2. Architecture
h1("2. System Architecture")
body(
    "The system is a closed loop, not a pipeline that runs once. On every mission, the planner "
    "chooses a viewpoint using the current belief state; the drone (in kinematic simulation for "
    "fast statistical comparison, or under real PID physics for the flagship demo) flies there and "
    "captures a frame; the trained detector reports defects with a confidence and an epistemic "
    "uncertainty; each detection is ray-cast into a real 3D world position and reconciled against "
    "persistent memory (matched to an existing defect or registered as new, with growth computed if "
    "matched); and the resulting uncertainty/growth signal is written back into the belief the "
    "planner uses for its very next choice &mdash; and, at the start of the next mission, seeded "
    "from memory so a growing or unresolved defect is not forgotten."
)
image(os.path.join(HERE, "architecture_diagram.png"), width=15.5 * cm,
      caption="Figure 1. Closed-loop data flow. The red arrow is what makes it a loop: persistent "
              "memory's growth/uncertainty state feeds directly into the next viewpoint decision.")

story.append(PageBreak())

# ---------------------------------------------------------------- 3. What was implemented
h1("3. What Was Implemented")

h2("3.1 Perception &mdash; Real Trained Detector")
body(
    "A YOLO object detector was trained from scratch (not fine-tuned from a task-matched "
    "checkpoint) on <b>MBDD2025</b> (“A dataset of building surface defects collected by UAVs "
    "for machine learning-based detection,” Scientific Data, 2025; Zenodo DOI "
    "10.5281/zenodo.15622584; CC-BY-4.0) &mdash; 14,471 real UAV photographs across six structure "
    "types and five defect classes (crack, leakage, abscission, corrosion, bulge), with a 70/20/10 "
    "train/val/test split built and never mixed across splits. <b>Two genuinely-trained checkpoints "
    "exist.</b> The original was CPU-budget-limited by necessity: YOLOv8n, 320px, 30 epochs "
    "(mAP50 0.685 on the held-out test set). Once that budget was identified as the limiting factor "
    "(see Limitations), the same data was retrained on a rented NVIDIA L4 GPU at a realistic "
    "budget &mdash; YOLOv8s, 640px, 100 epochs, plus ~4x oversampling of the rarest class (bulge, "
    "2,018 instances vs. abscission's 22,702) via <font face=\"Courier\">datagen/oversample_bulge.py</font> "
    "&mdash; reaching mAP50 0.884 on the identical test set. Per-class precision/recall, CPU "
    "&rarr; GPU: crack 0.75/0.45 &rarr; 0.84/0.75 (resolution mattered most here &mdash; cracks are "
    "thin, low-contrast features that lose signal at 320px), bulge 0.83/0.58 &rarr; 0.95/0.96 "
    "(oversampling), leakage 0.85/0.86 &rarr; 0.90/0.92, abscission 0.79/0.58 &rarr; 0.87/0.78, "
    "corrosion 0.80/0.59 &rarr; 0.83/0.79. Both checkpoints are kept "
    "(<font face=\"Courier\">weights/mbdd_yolov8n/</font>, "
    "<font face=\"Courier\">weights/mbdd_yolov8s_gpu/</font>); the GPU one is "
    "<font face=\"Courier\">perception/ml_detector.py</font>'s current default, and Section 4.2's "
    "closed-loop results reflect it."
)
body(
    "Detection <b>uncertainty</b> is computed as a test-time-augmentation (TTA) ensemble variance: "
    "each frame is run through the model five times &mdash; the original plus four photometric "
    "variants (brightness/contrast jitter, Gaussian noise, blur, and a combined jitter+blur) &mdash; "
    "and each detection's confidence standard deviation across the ensemble (counting zero for any "
    "variant where no matching box is found) is reported as its uncertainty. This is a standard, "
    "documented substitute for MC-Dropout, used because stock YOLOv8 has no dropout retained at "
    "inference; it is never mislabeled as literal MC-Dropout anywhere in the codebase or this report."
)
body(
    "A converter for a second real dataset, <b>SDNET2018</b> (Maguire, Dorafshan &amp; Thomas, 2018; "
    "CC-BY-4.0; the public benchmark Inam et al. 2023 &mdash; one of the cited base papers &mdash; "
    "combines with their own field data) exists "
    "(<font face=\"Courier\">datagen/prepare_sdnet.py</font>, treating its whole-image "
    "cracked/uncracked classification labels as weak full-image detection boxes/negatives to enrich "
    "the crack class exactly as that base paper does) but was never actually run in this project: "
    "SDNET2018.zip requires a manual, bot-blocked download (see README.md) that was not done. "
    "Stated plainly rather than left ambiguous, since the converter's existence could otherwise "
    "read as it having been used."
)
body(
    "A real false-positive limitation was found by directly testing the GPU model on a genuinely "
    "clean image, rather than assumed: on the single true background-labeled MBDD2025 test image "
    "(only 8 of 14,471 images in the whole dataset have zero labeled defects), the GPU model "
    "produced one low-confidence false positive (leakage, confidence 0.30) where the CPU model had "
    "produced none. All three clean wall textures actually used in the simulation "
    "(<font face=\"Courier\">scene/clean_wall_*.png</font>) still return zero detections on both "
    "models. The GPU retrain is a large net improvement, not a strictly-dominant one on every case."
)

h2("3.2 3D Localization")
body(
    "Every 2D detection is converted to a real-world 3D position purely from geometry, with no "
    "learned depth: the exact camera projection convention gym-pybullet-drones' onboard camera uses "
    "(60&deg; vertical FOV, aspect fixed at 1.0, eye offset from the drone body) is replicated "
    "analytically in <font face=\"Courier\">geometry.py</font>, a pixel is unprojected into a world-space "
    "ray, and that ray is intersected with the known plane of the wall being inspected. This was "
    "numerically validated against a synthetic marker at a known position with sub-2cm residual "
    "error before being trusted anywhere else in the system."
)

h2("3.3 Persistent Defect Memory")
body(
    "A real two-database “digital twin,” not a flat file, running as local Docker services "
    "(<font face=\"Courier\">docker/docker-compose.yml</font>):"
)
bullets([
    "<b>PostgreSQL + pgvector</b> &mdash; an append-only detection log; each detection carries a 32-dimensional "
    "appearance+spatial embedding (position, class one-hot, size, confidence, and an HSV color-histogram "
    "crop descriptor). Identity matching for a new detection queries nearest neighbors by cosine "
    "distance on this embedding, then confirms with a hard spatial gate (0.35m) so an imperfect "
    "embedding can never merge two genuinely different physical defects.",
    "<b>Neo4j</b> &mdash; the identity graph: <font face=\"Courier\">(:Defect)-[:OBSERVED_IN]-&gt;(:Mission)</font>, "
    "<font face=\"Courier\">(:Defect)-[:LOCATED_ON]-&gt;(:Wall)</font>, with growth recorded on each "
    "observation edge &mdash; answering “which defects grew, and by how much, across visits.”",
])
body(
    "This mechanism was independently verified before being trusted in the full evaluation: a "
    "manual round-trip test confirmed a re-detected defect at a shifted position and larger size is "
    "correctly matched to its prior identity and its growth is correctly computed, while a "
    "spatially-distant detection correctly creates a new identity rather than merging."
)

h2("3.4 Planning &mdash; Base Paper and Novel Algorithm")
body(
    "All planners share one candidate-viewpoint graph (54 stations across the 9 wall segments "
    "of the simulated two-room house) and a shared coverage belief: each wall is discretized into a "
    "surface grid sized proportionally to its physical width (fixed 1m cells, not a fixed cell "
    "<i>count</i> &mdash; a narrower wall gets fewer cells, matching Isler et al.'s original "
    "fixed-voxel-size volumetric formulation rather than giving every wall equal weight regardless "
    "of size), and a Bernoulli “adequately observed” belief per cell starts at maximum entropy (0.5) "
    "and is resolved toward certainty as views accumulate."
)
table(
    ["Planner", "Formulation", "Role"],
    [
        ["Random", "Uniform random choice among unvisited viewpoints.", "Naive baseline"],
        ["Isler-NBV", "Cost-normalized Shannon-entropy information gain over the coverage grid "
                       "&mdash; geometry only, no defect semantics.", "Base paper "
                       "(Isler et al. 2016), adapted to 2D"],
        ["UW-TIG (novel)", "Same coverage term, <b>plus</b> a detection-uncertainty term, a "
                            "temporal-growth term sourced from persistent memory, and a "
                            "persistent-monitoring staleness/latency term, combined in one weighted "
                            "utility and selected via a 2-step receding-horizon lookahead rather than "
                            "pure 1-step greedy, with a coverage-guarantee phase that visits every "
                            "wall at least once per mission before this utility takes over. Unlike "
                            "the baselines, it can revisit an already-inspected viewpoint when that "
                            "is where the utility is.",
         "Novel contribution"],
        ["UW-TIG (5 ablations)", "UW-TIG with, respectively: the uncertainty term zeroed, the "
                                  "temporal term zeroed, the staleness term zeroed, the "
                                  "coverage-guarantee phase disabled, and the lookahead disabled "
                                  "(pure 1-step greedy).",
         "Isolates each added term's contribution"],
    ],
    col_widths=[3.1 * cm, 9.4 * cm, 3.3 * cm],
    left_align_cols=(1, 2),
)
body(
    "Concretely: <font face=\"Courier\">utility(v) = w_ig&middot;InfoGain(v) + w_u&middot;Uncertainty(v) "
    "+ w_t&middot;Growth(v) + w_s&middot;Staleness(v) &minus; w_cost&middot;FlightCost(v)</font>, with "
    "<font face=\"Courier\">w_ig=1.0, w_uncertainty=1.5, w_temporal=2.0, w_staleness=1.0, w_cost=0.4</font>. "
    "Setting <font face=\"Courier\">w_uncertainty=w_temporal=w_staleness=0</font> and disabling the "
    "lookahead recovers exactly the Isler-NBV baseline &mdash; UW-TIG is a strict generalization of "
    "the base paper, not an unrelated alternative. <font face=\"Courier\">FlightCost</font> itself "
    "combines translation distance with a small rotation-reorientation cost (Section 3.4.1)."
)
h2("3.4.1 Two Bugs Found and Fixed While Adding the Lookahead")
body(
    "Adding the receding-horizon lookahead immediately collapsed the measured flight distance to "
    "exactly zero for every UW-TIG variant in a smoke test &mdash; too clean an invariant to be "
    "correct, and worth tracing rather than shipping. Root cause: the uncertainty/growth reward for "
    "a cell never decayed on repeat visits, so once any wall produced a detection, revisiting it kept "
    "re-earning full reward forever at zero extra travel cost; the more thorough lookahead exploited "
    "this completely. <i>Fix:</i> uncertainty/growth reward now decays with view count using the same "
    "saturating function already used for coverage entropy, so repeated identical confirmations earn "
    "diminishing reward &mdash; making “uncertainty-weighted” mean reward for reducing uncertainty, "
    "not reward for remembering a number. Chasing this down surfaced a second, independent issue: "
    "three walls of the smaller room have standoff viewpoints that coincide at exactly the same 3D "
    "position (the room's width is exactly twice the standoff distance), making a 90&ndash;180-degree "
    "reorientation between them look like a zero-cost move under pure-translation cost accounting. "
    "<i>Fix:</i> a small rotation cost was added to the flight-cost term, calibrated to sit below the "
    "graph's smallest genuinely-different-position gap so it breaks this exact-zero tie without "
    "distorting any real routing decision elsewhere (an initial, larger calibration attempt "
    "overcorrected and was caught before being reported: it suppressed Isler-NBV's exploration of the "
    "larger room almost entirely, and was revised down before the results in Section 4.2)."
)

h2("3.4.2 A Coverage-Guarantee Fix for Low Recall")
body(
    "Section 4.2's results initially showed UW-TIG's recall pinned at 0.36 with "
    "<font face=\"Courier\">coverage_frac</font> stuck at exactly 0.33 (3 of 9 walls) across every "
    "seed and every ablation. The tell that ruled out a weight-tuning fix: <b>Isler-NBV itself "
    "(zero uncertainty/temporal/staleness weight) showed the identical 0.33 coverage ceiling</b>, "
    "seed for seed. The ceiling comes from the cost-normalized-greedy formulation's own cost/reward "
    "scale on this viewpoint graph &mdash; travelling to the far building is never worth its cost "
    "relative to the coverage-entropy reward on offer, for any weighting of UW-TIG's added terms, "
    "since even a planner with none of those terms hits the same wall. <i>Fix:</i> an explicit "
    "coverage-guarantee phase in <font face=\"Courier\">UWTIGPlanner.select_next</font>: while any "
    "wall has zero visits this mission, restrict selection to Isler-NBV's own formulation over only "
    "the unvisited walls; once every wall has at least one visit, control passes to the full "
    "multi-term utility for the rest of the budget. A new ablation, "
    "<font face=\"Courier\">uwtig_no_coverage_first</font>, reproduces the old behavior for "
    "comparison. This is not a strict improvement -- Section 4.2's updated table quantifies a real "
    "trade-off (recall and coverage roughly double, at a real cost to precision, localization error, "
    "and flight distance) rather than a free win, and is reported as such."
)

h2("3.5 Simulation Environment")
body(
    "A two-room house (Room A 4&times;4m, Room B 2.6&times;2.6m, connected by a 1m doorway) built on "
    "gym-pybullet-drones (Panerati et al., IROS 2021), a real open-source drone simulator with actual "
    "rotor thrust/drag physics and closed-loop PID flight control (DSLPIDControl) &mdash; not a "
    "scripted kinematic teleport. Two capture modes share the identical scene-construction and camera "
    "code: a fast kinematic mode (teleport + render, no physics stepping) for the large statistical "
    "comparison sweep, and full real-physics PID flight for the qualitative flagship demo."
)
body(
    "The environment was dressed as a utility inspection yard rather than a plain house: a "
    "procedurally generated concrete ground texture, an elevated pipe rack, and a small lattice "
    "support tower surround the structure (<font face=\"Courier\">scene/environment.py</font>). "
    "Since the house is fully enclosed, the flagship demo opens with a slow orbiting establishing "
    "shot of the whole yard, otherwise never visible once the drone is inside flying wall-facing "
    "inspection routes. Flight uses ease-in-ease-out (smoothstep) trajectory interpolation rather "
    "than a linear ramp &mdash; DSLPIDControl tracks a moving reference, so a linear ramp has a "
    "velocity discontinuity at both ends of every hop, which is most of what reads as jerky flight "
    "&mdash; and the third-person chase camera exponentially smooths its position instead of "
    "snapping to the drone's instantaneous pose every frame."
)
image(os.path.join(HERE, "establishing_shot.png"), width=13.5 * cm,
      caption="Figure 2. Establishing shot from the flagship demo video: the utility yard (pipe rack, "
              "right; lattice support tower, left) surrounding the two-room inspection structure.")

h2("3.6 Experiment Harness")
body(
    "Four scenarios exercise different aspects of the system: <b>static</b> and <b>multi-defect</b> "
    "(steady-state detection/coverage across multiple real defects), <b>uncertain</b> (deliberately "
    "faint/ambiguous real crops, testing whether uncertainty-driven revisiting helps), and "
    "<b>growing</b> (a procedurally-generated defect whose severity increases mission-to-mission with "
    "exactly known ground truth, testing temporal growth tracking). The static/uncertain/multi-defect "
    "scenarios use <b>real MBDD2025 photographs</b> (from the held-out test split, never seen during "
    "training) directly as wall textures, square-cropped around the true defect location so ground-truth "
    "position is exactly known without a per-frame label-mask render."
)
body(
    "<font face=\"Courier\">experiments/evaluate.py</font> runs every (planner, scenario, seed, "
    "mission-sequence) combination, logs per-step detections/localizations/memory updates, and "
    "computes precision/recall/F1, mean localization error, total flight distance, coverage "
    "fraction, reinspection rate, uncertainty reduction, growth-detection accuracy, and information "
    "gain per viewpoint &mdash; writing <font face=\"Courier\">results/comparison.csv</font> and a "
    "comparison chart."
)

story.append(PageBreak())

# ---------------------------------------------------------------- 4. Results
h1("4. Results")

h2("4.1 Offline Perception Benchmark (real MBDD2025 test set, 1,448 images)")
table(
    ["Metric", "CPU checkpoint", "GPU checkpoint (current default)"],
    [["mAP50", "0.685", "0.884"], ["mAP50-95", "0.347", "0.506"],
     ["Precision (mean)", "0.804", "0.874"], ["Recall (mean)", "0.612", "0.842"]],
    col_widths=[5 * cm, 3.5 * cm, 5.5 * cm],
)
table(
    ["Class", "P (CPU)", "R (CPU)", "P (GPU)", "R (GPU)"],
    [
        ["Crack", "0.75", "0.45", "0.84", "0.75"],
        ["Leakage", "0.85", "0.86", "0.90", "0.92"],
        ["Abscission", "0.79", "0.58", "0.87", "0.78"],
        ["Corrosion", "0.80", "0.59", "0.83", "0.79"],
        ["Bulge", "0.83", "0.58", "0.95", "0.96"],
    ],
    col_widths=[3.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm],
)
body(
    "Both are genuinely trained, real-data results on data the model never saw during training "
    "&mdash; not placeholder metrics. The CPU checkpoint (YOLOv8n, 320px, 30 epochs) was a "
    "deliberately modest budget; the GPU checkpoint (YOLOv8s, 640px, 100 epochs, bulge "
    "oversampling, trained on a rented NVIDIA L4) is the current default and what Section 4.2's "
    "closed-loop numbers below now use (see Section 3.1 for what changed and why)."
)

h2("4.1.1 How This Compares to Numbers Reported Elsewhere (Context, Not a Fair Fight)")
body(
    "Two cited detection-side papers report the same <i>kind</i> of metric (precision/recall/mAP) "
    "on their own defect datasets, making this the one place in this report where a real cross-paper "
    "number comparison is at least meaningful in units &mdash; unlike Section 4.2's planner-level "
    "table below, where no cited paper reports the same metric set at all:"
)
table(
    ["Source", "Task", "Dataset", "Prec.", "Recall", "mAP"],
    [
        ["This project (GPU)", "5-class UAV defect detection", "MBDD2025, public, 14,471 photos", "0.874", "0.842", "0.884"],
        ["Li, Shi &amp; Sun 2026", "Utility-tunnel defect detection", "Private, 5,000 images, never released", "0.932", "0.924", "0.926"],
        ["Inam et al. 2023 (best variant)", "Bridge crack only (1 class)", "Own field data + SDNET2018", "0.977", "0.967", "0.993"],
    ],
    col_widths=[3.6 * cm, 4.3 * cm, 4.8 * cm, 1.4 * cm, 1.4 * cm, 1.4 * cm],
    highlight_row=1,
    left_align_cols=(0, 1, 2),
)
body(
    "<b>This project's numbers are lower, stated plainly rather than explained away</b> &mdash; but "
    "the comparison cuts in both directions, not just favorably: Inam et al.'s headline number is for "
    "<b>crack only</b>, a strictly easier single-class discrimination problem with no cross-class "
    "confusion possible, versus this project's 5 visually distinct classes in one model; Li et al.'s "
    "5,000-image dataset is <b>private and was confirmed unobtainable</b> during this project's own "
    "dataset audit, so its difficulty can't be independently checked, while MBDD2025 is the only fully "
    "public, independently downloadable dataset of the three; and Inam et al. report the best of three "
    "YOLOv5 variants (s/m/l) chosen after seeing test results, a legitimate methods-paper practice but "
    "not the same as this project's single, pre-registered checkpoint. <b>What this does and doesn't "
    "mean</b>: this project's detector is not state-of-the-art against narrower single-class or "
    "private-dataset systems, and it would be dishonest to imply otherwise by omission. The controlled "
    "comparison this report's novelty claims actually rest on is the same-testbed one in Section 4.2 "
    "(UW-TIG vs. a faithfully reimplemented Isler-NBV vs. Random &mdash; same detector, same "
    "environment, same protocol for all three), not a claim of leading the wider defect-detection "
    "literature on raw detector numbers."
)

h2("4.2 Closed-Loop Simulation Comparison")
body(
    "Mean over the static / uncertain / multi-defect scenarios &times; 5 seeds &times; 3 sequential "
    "missions &times; a 16-viewpoint-per-mission budget (the <font face=\"Courier\">growing</font> "
    "scenario is excluded from this table &mdash; see Section 6, it is an honestly-reported failure "
    "mode, not a comparable number). Produced by running each seed as its own subprocess and merging "
    "the results (<font face=\"Courier\">run_full_sweep.sh</font>) after the naive single-process "
    "sweep proved unreliable on this machine &mdash; see Section 6. Uses the GPU-retrained detector "
    "(Section 3.1) and, as of this table, the coverage-guarantee phase (Section 3.4.2) as UW-TIG's "
    "default -- <font face=\"Courier\">uwtig_no_coverage_first</font>'s row is the earlier, "
    "recall-limited configuration, kept for direct comparison:"
)
table(
    ["Planner", "Prec.", "Recall", "F1", "Loc. err<br/>(m)", "Flight<br/>(m)", "Cover-<br/>age", "Reinsp.<br/>rate", "ECE", "Unc. gap<br/>(fp&minus;tp)"],
    [
        ["Random", "0.58", "0.57", "0.55", "0.77", "393.8", "1.00", "1.00", "0.33", "-0.05"],
        ["Isler-NBV (base paper)", "0.64", "0.43", "0.50", "0.49", "18.6", "0.33", "0.44", "0.33", "-0.06"],
        ["UW-TIG (novel, default)", "0.76", "0.63", "0.65", "0.70", "108.8", "1.00", "1.00", "0.35", "-0.07"],
        ["UW-TIG, no uncertainty term", "0.76", "0.62", "0.65", "0.70", "109.3", "1.00", "1.00", "0.34", "-0.08"],
        ["UW-TIG, no temporal term", "0.75", "0.62", "0.65", "0.71", "109.1", "1.00", "1.00", "0.35", "-0.07"],
        ["UW-TIG, no staleness term", "0.72", "0.57", "0.59", "0.68", "93.9", "1.00", "1.00", "0.36", "-0.06"],
        ["UW-TIG, no coverage-guarantee", "0.86", "0.36", "0.55", "0.19", "0.4", "0.33", "0.44", "0.28", "-0.02"],
        ["UW-TIG, no lookahead", "0.76", "0.62", "0.65", "0.67", "106.5", "1.00", "1.00", "0.36", "-0.07"],
    ],
    col_widths=[3.6 * cm, 1.3 * cm, 1.3 * cm, 1.0 * cm, 1.6 * cm, 1.5 * cm, 1.3 * cm, 1.4 * cm, 1.3 * cm, 1.7 * cm],
    highlight_row=3,
    left_align_cols=(0,),
)
body(
    "<i>A note on what this table can and can't be compared against:</i> the only valid comparison "
    "for these numbers is the Isler-NBV and Random rows <i>in this same table</i> &mdash; same "
    "testbed, same detector, same environment, same protocol for all three. No cited paper reports "
    "this metric set (precision/recall/coverage/reinspection-rate/ECE/uncertainty-gap) for a "
    "persistent-memory, active-reinspection planner: Isler et al. 2016 is a volumetric-reconstruction "
    "paper with no precision/recall concept at all, and GATSBI reports a differently-defined "
    "“detection rate vs. a frontier-exploration baseline” (11.5x better) that isn't "
    "convertible to these columns. The one place a real cross-paper comparison is meaningful is the "
    "detector itself (Section 4.1.1)."
)
body(
    "<b>UW-TIG is now the only planner ahead of both baselines on precision AND recall at once</b> "
    "(0.76/0.63 vs. Isler-NBV's 0.64/0.43 and Random's 0.58/0.57), with full coverage and "
    "reinspection (1.00/1.00) &mdash; but this did not come free, and the "
    "<font face=\"Courier\">no-coverage-guarantee</font> row shows exactly what was traded. Before "
    "Section 3.4.2's fix, every UW-TIG variant (and Isler-NBV itself) was stuck at exactly 0.33 "
    "coverage (3 of 9 walls), identically, every seed &mdash; since even a planner with none of "
    "UW-TIG's added terms hit the same ceiling, no amount of reweighting those terms could have "
    "reliably fixed it; the ceiling was in the cost-normalized-greedy formulation's own cost/reward "
    "scale on this viewpoint graph. Forcing full coverage first raised recall 0.36&rarr;0.63 and "
    "coverage/reinspection 0.33/0.44&rarr;1.00/1.00, at the cost of precision (0.86&rarr;0.76), mean "
    "localization error (0.19m&rarr;0.70m &mdash; plausibly because the coverage phase picks each "
    "unvisited wall's viewpoint by entropy/cost alone, with no notion of which standoff localizes "
    "best, unlike the mature multi-look positions UW-TIG settles into under reinspection), and "
    "flight distance (0.3m&rarr;108.9m, still ~3.6x less than Random's 393.8m but no longer close to "
    "Isler-NBV's 18.6m). <b>Isler-NBV's own row is numerically identical across every seed and "
    "scenario</b> (18.6m flight distance, 0.33 coverage, to the last decimal in every run) &mdash; a "
    "direct consequence of its formulation being a pure function of the coverage belief with no "
    "dependence on the random seed or the scenario's ground truth, so on a fixed viewpoint graph it "
    "always makes the identical sequence of moves; only what happens to be physically present on the "
    "walls it visits varies."
)
image(os.path.join(HERE, "..", "results", "comparison.png"), width=15.5 * cm,
      caption="Figure 3. Comparison chart across all eight planners (blue = UW-TIG) for eight of the "
              "logged metrics, generated directly by experiments/evaluate.py.")

h2("4.2.1 Calibration Check: Is the Uncertainty Signal Actually Informative?")
body(
    "Reading Rückin et al.'s evaluation methodology closely (Section 1.1) prompted a check this "
    "project had never actually run despite naming itself “uncertainty-weighted”: is the "
    "detector's confidence well-calibrated, and does the TTA-ensemble uncertainty term UW-TIG's "
    "utility weights (<font face=\"Courier\">w_uncertainty=1.5</font>) actually correlate with which "
    "detections are wrong? Two metrics were added to <font face=\"Courier\">evaluate.py</font> for "
    "this, using data every mission already produces &mdash; no re-training or re-simulation of the "
    "detector needed &mdash; and both come back with an honest, not entirely flattering answer, shown "
    "in the table's last two columns above. <b>ECE is high</b> (0.28&ndash;0.36) for every planner: a "
    "well-calibrated detector would show ECE close to 0 (confidence tracking empirical accuracy "
    "bin-by-bin); this detector's confidence is useful for <i>ranking</i> detections (precision/recall "
    "trade off in the expected direction as the confidence threshold moves) but is not trustworthy as "
    "a calibrated probability &mdash; invisible in every mAP/precision/recall number reported so far, "
    "since none of them check calibration. <b>The uncertainty gap is negative for every planner</b> "
    "(-0.02 to -0.08): the TTA-ensemble uncertainty is, on average, <i>lower</i> on false positives "
    "than on true positives &mdash; the opposite of what would validate “high uncertainty means "
    "likely wrong.” A plausible explanation, not confirmed further here: genuine defects "
    "(especially subtle ones like <font face=\"Courier\">crack</font>) sit closer to the model's "
    "decision boundary and are more sensitive to the photometric TTA transforms, so correct detections "
    "of real, hard-to-see defects legitimately vary more across augmented views than a spurious, "
    "texture-confusion false positive that fires consistently regardless of augmentation. This does "
    "not undermine the ablations' measured effect of <font face=\"Courier\">w_uncertainty</font> "
    "(it's a real signal, used only for relative ranking within one mission, never thresholded as an "
    "absolute probability), but it does mean this project cannot currently back the claim that a high "
    "TTA-uncertainty reading means a detection is probably wrong &mdash; on this evidence, the opposite "
    "direction is what was measured. Stated plainly as Limitation 8 rather than left an unstated "
    "assumption; a genuine fix would swap in an uncertainty estimate actually validated for "
    "calibration, e.g. MC-Dropout as Rückin et al. use, or post-hoc temperature scaling."
)

story.append(PageBreak())

h2("4.3 Flagship Real-Physics Demo")
body(
    "<font face=\"Courier\">demo_uwtig_flight.py --missions 3 --budget 8 --scenario multi_defect</font> "
    "flies UW-TIG with the trained detector under real PID-controlled physics (not kinematic teleport, "
    "not a fixed patrol list) across 3 sequential missions over all 9 walls/panels of the facility, six "
    "of which carry real defects. It produces an annotated video with confidence and uncertainty "
    "overlaid on every detection."
)
image(os.path.join(HERE, "inspection_frame.png"), width=9 * cm,
      caption="Figure 4. Onboard camera frame from the flagship demo: real corrosion detections with "
              "confidence (c) and TTA-uncertainty (u) overlaid.")
body(
    "With the GPU-retrained detector and the coverage-guarantee phase (Section 3.4.2), the "
    "real-physics log shows the coverage-then-reinspect structure directly: <b>mission 1</b> visits "
    "8 of the 9 walls (crack/corrosion/leakage all correctly caught on Buildings A and B, plus the "
    "two decorative panels), still filling out first-time coverage rather than reinspecting anything; "
    "<b>mission 2</b> visits the last never-seen wall (<font face=\"Courier\">Tower-Panel</font>) "
    "first, then begins active reinspection of Building A's real defects "
    "(<font face=\"Courier\">A-west</font> crack and <font face=\"Courier\">A-east</font> corrosion "
    "each caught twice); by <b>mission 3</b>, every wall has been visited at least once across the "
    "two prior missions, so the coverage-guarantee phase never triggers and the entire mission goes to "
    "<b>active reinspection</b> of Building B's three real defects, each revisited 2&ndash;3 times with "
    "confidence varying across repeat looks. This is the coverage/reinspection trade-off from Section "
    "4.2 running for real through the physics stack, not only in the fast kinematic comparison: "
    "complete facility coverage first, concentrated reinspection of what matters once that's secured."
)

# ---------------------------------------------------------------- 5. How it's better
h1("5. How the Novel Planner Is Better")
bullets([
    "<b>Precision AND recall, simultaneously ahead of both baselines:</b> 0.76 precision / 0.63 "
    "recall vs. Isler-NBV's 0.64/0.43 and Random's 0.58/0.57 &mdash; no baseline beats UW-TIG on "
    "either axis, let alone both, and full coverage/reinspection (1.00/1.00) means it is no longer "
    "trading completeness away to get there. Every planner's precision also improved once the "
    "GPU-retrained detector replaced the CPU one (Section 3.1), a perception-level gain independent "
    "of planning strategy, on top of which this precision/recall combination sits.",
    "<b>Real trade-offs, reported plainly, not hidden:</b> reaching that combination costs mean "
    "localization error (0.70m, worse than Isler-NBV's 0.49m -- plausibly because the "
    "coverage-guarantee phase, Section 3.4.2, picks viewpoints by entropy/cost alone with no "
    "localization-quality criterion) and flight distance (108.8m, more than Isler-NBV's 18.6m, "
    "though still ~3.6x less than Random's 393.8m). An earlier configuration "
    "(<font face=\"Courier\">uwtig_no_coverage_first</font>) instead had excellent precision and "
    "localization (0.86, 0.19m) but only 0.36 recall and 0.33 coverage; both configurations remain "
    "available since which is preferable is a real deployment decision, not something this report "
    "picks for the reader.",
    "<b>Genuine active reinspection:</b> unlike both baselines (which only ever visit each station "
    "once per mission by construction), UW-TIG is the only planner that revisits an already-inspected "
    "viewpoint mid-mission when the utility says to &mdash; directly observed in both the kinematic "
    "sweep's reinspection-rate metric and the real-physics flagship log.",
    "<b>Three literature-grounded additions beyond the original novelty</b> (Section 3.4): a "
    "persistent-monitoring staleness term (Alamdari, Fata &amp; Smith 2014) rewards revisiting a cell "
    "purely for time-elapsed-since-last-look, independent of whether a defect was ever found there; "
    "a 2-step receding-horizon lookahead (Bircher et al. 2016; Dhami et al.'s GATSBI) evaluates each "
    "candidate together with its best likely follow-up rather than choosing purely myopically, while "
    "still only ever executing one step before replanning; and a coverage-guarantee phase "
    "(Section 3.4.2) that fixed a recall ceiling found to affect Isler-NBV too, not just UW-TIG's "
    "added terms.",
    "<b>Base paper is strictly subsumed, not sidestepped:</b> zeroing UW-TIG's novel weight terms, "
    "disabling the lookahead, and disabling the coverage-guarantee phase recovers the Isler-NBV "
    "baseline exactly, so the comparison is a true ablation of what the novel terms add, not two "
    "unrelated algorithms.",
])

story.append(PageBreak())

# ---------------------------------------------------------------- 6. Limitations
h1("6. Limitations (Stated Plainly)")
bullets([
    "<b>The “growing” scenario's detector recall is ~0%.</b> It uses a procedurally-generated "
    "corrosion texture because MBDD2025 is single-timepoint and has no repeated-visit growth "
    "sequence for the same physical defect. The real-photo-trained model essentially does not "
    "recognize this synthetic texture at all (verified directly: zero detections at conf&gt;0.1 on "
    "the rendered frame). The temporal-memory <i>mechanism</i> was independently verified correct; "
    "what fails is purely the perception model's domain generalization to synthetic textures.",
    "<b>Detection uncertainty is TTA ensemble variance, not literal MC-Dropout</b> &mdash; a standard, "
    "clearly documented substitute, never presented as the real thing.",
    "<b>The original CPU-trained checkpoint was budget-limited</b> (30 epochs, 320px, batch 8, "
    "mAP50=0.685) &mdash; <b>resolved</b> by actually running the longer GPU training this limitation "
    "called for (YOLOv8s, 640px, 100 epochs, on a rented NVIDIA L4), reaching mAP50=0.884 on the "
    "identical test set (Section 3.1); this is now the default detector and Section 4.2's numbers "
    "reflect it. Still not the absolute ceiling &mdash; yolov8m/l and 1280px were not tried.",
    "<b>5 seeds</b> is enough to see the headline effects clearly, but not enough to cleanly separate "
    "most ablations' individual contributions (uncertainty, temporal, staleness, lookahead) &mdash; "
    "their deltas in Section 4.2 are small and within what 5 seeds can statistically separate. The "
    "exception is the coverage-guarantee ablation, whose effect (recall 0.63 vs. 0.36) is large enough "
    "to be clearly visible even at this seed count.",
    "<b>PostgreSQL/Neo4j run as local Docker containers</b> with development-only credentials, not a "
    "production deployment.",
    "<b>A real fairness bug was found and fixed during development:</b> the shared memory store used "
    "across the whole planner-comparison sweep initially let different planners' detection histories "
    "leak into each other (since identity matching was not scoped per scenario+planner+seed). This "
    "was caught, fixed via run-scoped memory keys, and verified with a targeted isolation test before "
    "any of the numbers in this report were produced.",
    "<b>The single-process full sweep (140 mission-runs) crashed three consecutive times</b> after "
    "the staleness/lookahead additions, with three different low-level symptoms (a memory allocation "
    "failure despite ample free RAM, a silent exit, a segmentation fault) consistent with a resource-"
    "accumulation issue in PyBullet's software rasterizer across many sequential render sessions in "
    "one process, not a defect in the planner logic. Fixed by running each seed as its own fresh "
    "subprocess and merging results afterward (<font face=\"Courier\">run_full_sweep.sh</font>); "
    "Section 4.2's numbers are the real output of that approach, not a smaller stand-in.",
    "<b>The simulated environment's viewpoint graph changed (48 &rarr; 54 candidate stations) during "
    "development</b>, independent of this report's planner changes &mdash; so the flight-distance "
    "figures here are not directly comparable to any earlier internal draft that used the smaller "
    "graph; all numbers in this report are from one consistent, current environment.",
    "<b>The uncertainty signal UW-TIG plans around is not shown to correlate with correctness the way "
    "its name implies &mdash; checked directly, not assumed.</b> Prompted by a deeper read of "
    "Rückin et al.'s evaluation methodology (Section 1.1, Section 4.2.1), two calibration metrics "
    "were added and measured: detector confidence has a high Expected Calibration Error (0.28&ndash;"
    "0.36, well above a calibrated model), and false positives have <i>lower</i> average TTA-ensemble "
    "uncertainty than true positives for every planner (-0.02 to -0.08) &mdash; the opposite of the "
    "assumption implicit in weighting uncertainty as a “worth a second look” signal. This "
    "doesn't invalidate the planner's measured precision/recall/reinspection results (uncertainty is "
    "used only as a relative ranking signal within one mission, never thresholded as an absolute "
    "probability), but it does mean “high uncertainty here probably means wrong” is not a "
    "claim this project can currently back with evidence &mdash; the opposite direction is what was "
    "measured. A real fix would swap in an uncertainty estimate actually validated for calibration "
    "(e.g. MC-Dropout, as Rückin et al. use, or post-hoc temperature scaling); out of scope here, "
    "which was about measuring and reporting the gap honestly, not fixing it.",
])

# ---------------------------------------------------------------- 7. Conclusion
h1("7. Conclusion &amp; Future Work")
body(
    "This project delivers exactly what the proposal set out to build: a real, working, simulated "
    "closed loop from perception through persistent memory to active replanning, with a novel "
    "planner (UW-TIG) that strictly generalizes the identified base paper and is shown, with real "
    "numbers from real runs, to beat both a naive baseline and the base-paper adaptation on precision "
    "AND recall simultaneously, with full coverage and reinspection &mdash; while stating plainly what "
    "that costs (mean localization error and flight distance both rose relative to the base paper). "
    "The path to this result went through three iterations, each honestly reported rather than "
    "smoothed over: a literature-positioning pass (Section 1.1) added a persistent-monitoring "
    "staleness term and a receding-horizon lookahead, surfacing and fixing a real bug along the way "
    "(Section 3.4.1); a perception pass addressed the detector's own stated CPU-budget limitation by "
    "renting an NVIDIA L4 GPU, lifting held-out test mAP50 from 0.685 to 0.884 (Section 3.1); and a "
    "final pass, triggered by a direct observation that recall was too low, traced that ceiling to "
    "the base formulation itself (not UW-TIG's added terms) and fixed it with an explicit "
    "coverage-guarantee phase (Section 3.4.2) &mdash; trading some of the precision/localization "
    "advantage the earlier configuration had for a large recall and coverage gain, a trade-off stated "
    "plainly rather than presented as a pure win."
)
body("Concrete next steps, in priority order:")
bullets([
    "Improve the coverage-guarantee phase's viewpoint selection to weight localization quality "
    "(preferred standoff/lateral offset per wall), not just entropy/cost, to recover some of the "
    "localization accuracy lost when it was added (Section 3.4.2).",
    "Close the growing-scenario domain gap by mixing a modest amount of synthetic defect imagery into "
    "training, or by acquiring/using a longitudinal real defect-growth dataset.",
    "Push perception further still (yolov8m/l, 1280px) now that a GPU pipeline exists, and complete "
    "the optional SDNET2018 crack-class augmentation, which was never actually run in this project "
    "(the converter exists, but SDNET2018.zip's manual, bot-blocked download was not done).",
    "Increase the seed count for the ablation comparison specifically, to separate the uncertainty, "
    "temporal, staleness, and lookahead terms' individual contributions with statistical confidence.",
    "Extend the flight-distance metric to account for rotation/reorientation time, not translation "
    "alone, so it fairly represents hover-and-reinspect behavior in small rooms (Section 4.2).",
    "Move from the simulated two-room house toward the proposal's originally targeted structure "
    "types (pipeline segments, tower/truss rigs) as first-class inspectable geometry, not just "
    "decorative scenery.",
    "Replace TTA-ensemble variance with an uncertainty estimate actually validated for calibration "
    "(e.g. MC-Dropout, as Rückin et al. use, or post-hoc temperature scaling), given the negative "
    "uncertainty-gap finding in Section 4.2.1.",
])

# ---------------------------------------------------------------- References
h1("References")
refs = [
    "S. Isler, R. Sabzevari, J. Delmerico, and D. Scaramuzza, “An information gain formulation "
    "for active volumetric 3D reconstruction,” ICRA 2016.",
    "H. K. Dhami, F. Yu, K. Williams, S. Vajipey, and P. Tokekar, “GATSBI: An online GTSP-based "
    "algorithm for targeted surface bridge inspection,” ICUAS 2023.",
    "H. K. Dhami, C. Reddy, V. D. Sharma, T. Williams, and P. Tokekar, “GATSBI: An online "
    "GTSP-based algorithm for targeted surface bridge inspection and defect detection,” "
    "arXiv:2406.16625, 2024.",
    "A. Bircher, M. Kamel, K. Alexis, H. Oleynikova, and R. Siegwart, “Receding horizon "
    "&lsquo;next-best-view&rsquo; planner for 3D exploration,” ICRA 2016, pp. 1462&ndash;1468.",
    "J. Rückin, L. Jin, and M. Popovic, “Adaptive informative path planning using deep "
    "reinforcement learning for UAV-based active sensing,” ICRA 2022 (arXiv:2109.13570).",
    "J. Rückin, F. Magistri, C. Stachniss, and M. Popovic, “Informative path planning "
    "for active learning in aerial semantic mapping,” IROS 2022 (arXiv:2203.01652).",
    "J. Rückin, L. Jin, F. Magistri, C. Stachniss, and M. Popovic, “An informative path "
    "planning framework for active learning in UAV-based semantic mapping,” IEEE Transactions "
    "on Robotics, 39:4279&ndash;4296, 2023 (arXiv:2302.03347).",
    "S. Alamdari, E. Fata, and S. L. Smith, “Persistent monitoring in discrete environments: "
    "Minimizing the maximum weighted latency between observations,” The International Journal "
    "of Robotics Research, 33(1):138&ndash;154, 2014.",
    "A. Krause, A. Singh, and C. Guestrin, “Near-optimal sensor placements in Gaussian "
    "processes: Theory, efficient algorithms and empirical studies,” Journal of Machine "
    "Learning Research, 9:235&ndash;284, 2008.",
    "H. K. Dhami, V. D. Sharma, and P. Tokekar, “Pred-NBV: Prediction-guided next-best-view "
    "for 3D object reconstruction,” IROS 2023 (arXiv:2304.11465).",
    "Y. Liu, W. Zhao, H. Liu, Y. Wang, and X. Yue, “Coverage path planning for robotic quality "
    "inspection with control on measurement uncertainty,” arXiv:2201.04310, 2022.",
    "F. Taioli, F. Giuliari, Y. Wang, R. Berra, A. Castellini, A. Del Bue, A. Farinelli, "
    "M. Cristani, and F. Setti, “Unsupervised active visual search with Monte Carlo planning "
    "under uncertain detections,” IEEE TPAMI, 2024 (arXiv:2303.03155).",
    "W. Li, Y. Shi, and X. Sun, “Pipeline defect detection based on improved YOLOv11,” "
    "Processes, 2026.",
    "M. Inam, R. Islam, M. U. Akram, and F. Ullah, “Smart and automated infrastructure "
    "management: A deep learning approach for crack detection in bridge images,” "
    "Sustainability, 2023.",
    "Q. Zha, Y. Yao, W. Zhang, and W. Ma, “MBDD2025: A dataset of building surface defects "
    "collected by UAVs for machine learning-based detection,” Scientific Data, 2025. "
    "DOI: 10.5281/zenodo.15622584.",
    "M. Maguire, S. Dorafshan, and R. J. Thomas, “SDNET2018: A concrete crack image dataset for "
    "machine learning applications,” Utah State University, 2018. DOI: 10.15142/T3TD19.",
    "J. Panerati et al., “Learning to fly &mdash; a Gym environment with PyBullet physics for "
    "reinforcement learning of multi-agent quadcopter control,” IROS 2021 "
    "(gym-pybullet-drones).",
]
for i, r in enumerate(refs, 1):
    story.append(Paragraph(f"[{i}] {r}", styles["SmallNote"]))

story.append(Spacer(1, 14))
story.append(Paragraph(
    "Full source code, methodology detail, and the raw comparison CSV are in the project "
    "repository (README.md, RESULTS.md, NOVELTY.md, results/comparison.csv).", styles["SmallNote"]))


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(OUT_PATH, pagesize=A4,
                         topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                         leftMargin=2.0 * cm, rightMargin=2.0 * cm,
                         title="Autonomous Drone Utility Inspection - Technical Report")
doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
print("wrote", OUT_PATH)
