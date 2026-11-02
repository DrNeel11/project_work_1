const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

// Panel-review deck: 10 slides, white background, black text, no images.
// Structure follows the department's review format: problem, abstract,
// literature survey, inferences, architecture, requirements & data, model,
// results, conclusion. Closed-loop numbers are read from
// results/comparison.csv so the slides always match the latest sweep.
const THEME = {
  name: "Monochrome",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "000000", lt1: "FFFFFF", dk2: "404040", lt2: "D9D9D9",
    accent1: "000000", accent2: "595959", accent3: "808080",
    accent4: "A6A6A6", accent5: "262626", accent6: "BFBFBF",
    hlink: "000000", folHlink: "000000",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "UW-TIG project team";
pres.title = "UW-TIG: Closed-Loop Defect Inspection Planning";

const BLACK = "000000", WHITE = "FFFFFF", G1 = "404040", G2 = "595959", G3 = "808080",
  G4 = "BFBFBF", G5 = "D9D9D9", CARD = "F3F3F3";
const HEAD = THEME.headFontFace, BODY = THEME.bodyFontFace;
const X0 = 0.6, CW = 12.13; // content left edge and width

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { placeholder: {
        options: { name: "title", type: "title", x: X0, y: 0.35, w: CW, h: 0.7,
          fontFace: HEAD, fontSize: 26, bold: true, color: BLACK, align: "left", valign: "middle", margin: 0 },
        text: "",
      } },
    { line: { options: { x: X0, y: 1.12, w: CW, h: 0, line: { color: G5, width: 0.75 } } } },
    { line: { options: { x: X0, y: 1.12, w: 1.1, h: 0, line: { color: BLACK, width: 3 } } } },
    { text: {
        options: { x: X0, y: 7.05, w: 8, h: 0.3, margin: 0, fontFace: BODY, fontSize: 9, color: G3, align: "left" },
        text: "UW-TIG  ·  Closed-Loop Defect Inspection Planning",
      } },
    { placeholder: {
        options: { name: "pageNum", type: "body", x: 12.13, y: 7.05, w: 0.6, h: 0.3, margin: 0,
          fontFace: BODY, fontSize: 9, color: G3, align: "right", valign: "top" },
        text: "",
      } },
  ],
});

// ---------------------------------------------------------------- data
const RESULTS_CSV = path.join(__dirname, "..", "results", "comparison.csv");
const [HEADROW, ...LINES] = fs.readFileSync(RESULTS_CSV, "utf8").trim().split(/\r?\n/);
const COLS = HEADROW.split(",");
const ROWS = LINES.map((l) => Object.fromEntries(l.split(",").map((v, i) => [COLS[i], v])));
const MAIN_SCEN = ["static", "uncertain", "multi_defect"]; // growing excluded (known detector failure mode)
function meanOf(planner, col, scen = MAIN_SCEN) {
  const v = ROWS.filter((r) => r.planner === planner && scen.includes(r.scenario))
    .map((r) => parseFloat(r[col])).filter((x) => !Number.isNaN(x));
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : NaN;
}
const M = meanOf;
const f3 = (v) => (Number.isNaN(v) ? "--" : v.toFixed(3));
const f2 = (v) => (Number.isNaN(v) ? "--" : v.toFixed(2));
const f0 = (v) => (Number.isNaN(v) ? "--" : Math.round(v).toString());
const HAS = (p) => ROWS.some((r) => r.planner === p);
const SC = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "results", "scaleup_summary.json"), "utf8"));
const DET = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "results", "detector_extra.json"), "utf8"));
const SP = (set, p, k) => SC[set].planners[p][k];
const TS = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "results", "ten_seed_summary.json"), "utf8"));
const ci3 = (c) => (c ? `${c[0].toFixed(3)}-${c[1].toFixed(3)}` : "--");


// ---------------------------------------------------------------- helpers
let N = 0;
function slide(titleText) {
  const s = pres.addSlide({ masterName: "CONTENT" });
  s._no = ++N;
  if (titleText) s.addText(titleText, { placeholder: "title" });
  s.addText(String(s._no), { placeholder: "pageNum" });
  return s;
}

function text(s, t, o) {
  s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontFace: BODY, fontSize: 13, color: BLACK, valign: "top" }, o));
}

function bullets(s, items, o) {
  const opt = Object.assign({ fontSize: 13, gap: 8, color: BLACK }, o);
  // One paragraph per item: paragraph properties (bullet, spacing) ride on
  // the first run, the line break on the last run.
  const flat = [];
  items.forEach((it) => {
    const obj = typeof it === "object" ? it : { text: it };
    const runs = obj.lead
      ? [{ text: obj.lead + " ", options: { bold: true } }, { text: obj.text, options: {} }]
      : [{ text: obj.text, options: {} }];
    runs.forEach((r, i) => {
      const op = Object.assign({}, r.options);
      if (i === 0) Object.assign(op, { bullet: { code: "25AA", indent: 16 }, paraSpaceAfter: opt.gap });
      if (i === runs.length - 1) op.breakLine = true;
      flat.push({ text: r.text, options: op });
    });
  });
  s.addText(flat, { x: opt.x, y: opt.y, w: opt.w, h: opt.h, isTextBox: true, margin: 0, fontFace: BODY,
    fontSize: opt.fontSize, color: opt.color, valign: "top" });
}

function card(s, x, y, w, h, heading) {
  s.addShape("rect", { x, y, w, h, fill: { color: CARD }, line: { color: CARD, width: 0 } });
  if (heading) {
    text(s, heading, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.4, fontFace: HEAD, fontSize: 15, bold: true });
    s.addShape("line", { x: x + 0.25, y: y + 0.62, w: 0.6, h: 0, line: { color: BLACK, width: 2 } });
  }
}

function table(s, header, rows, o) {
  const opt = Object.assign({ fontSize: 11, rowH: 0.36, boldRow: -1 }, o);
  const head = header.map((h, ci) => ({
    text: h,
    options: { bold: true, color: WHITE, fill: { color: BLACK }, fontSize: opt.fontSize, fontFace: BODY,
      align: ci === 0 || (opt.leftCols || []).includes(ci) ? "left" : "center", valign: "middle" },
  }));
  const body = rows.map((row, ri) => row.map((cell, ci) => ({
    text: String(cell),
    options: { color: BLACK, fill: { color: ri % 2 ? CARD : WHITE }, fontSize: opt.fontSize, fontFace: BODY,
      bold: ri === opt.boldRow, valign: "middle",
      align: ci === 0 || (opt.leftCols || []).includes(ci) ? "left" : "center" },
  })));
  s.addTable([head, ...body], { x: opt.x, y: opt.y, w: opt.w, colW: opt.colW, rowH: opt.rowH,
    border: { type: "solid", color: G5, pt: 0.75 }, margin: [3, 6, 3, 6], autoPage: false });
}

function tile(s, x, y, w, h, value, label) {
  s.addShape("rect", { x, y, w, h, fill: { color: WHITE }, line: { color: BLACK, width: 1.25 } });
  text(s, value, { x, y: y + 0.18, w, h: h * 0.5, fontFace: HEAD, fontSize: 30, bold: true, align: "center", valign: "middle" });
  text(s, label, { x: x + 0.15, y: y + h * 0.6, w: w - 0.3, h: h * 0.35, fontSize: 11, color: G2, align: "center" });
}

const UW = {
  p: M("uwtig", "precision_confirmed"), r: M("uwtig", "recall_confirmed"), f: M("uwtig", "f1_confirmed"),
  fly: M("uwtig", "total_flight_dist_m"),
};
const RK = { f: M("ruckin_ipp", "f1_confirmed"), p: M("ruckin_ipp", "precision_confirmed"), fly: M("ruckin_ipp", "total_flight_dist_m") };
const FLY_LESS = Math.round(100 * (1 - UW.fly / RK.fly));

// ============================================================ 1. TITLE
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  N++;
  text(s, "AUTONOMOUS DEFECT INSPECTION PLANNING", { x: X0, y: 0.75, w: CW, h: 0.4, fontSize: 13, bold: true, color: G2, charSpacing: 3 });
  text(s, "UW-TIG: Uncertainty-Weighted Temporal Information Gain for Closed-Loop Defect Inspection",
    { x: X0, y: 1.2, w: 11.2, h: 1.3, fontFace: HEAD, fontSize: 30, bold: true });
  s.addShape("line", { x: X0, y: 2.7, w: 1.4, h: 0, line: { color: BLACK, width: 3 } });
  text(s, "PSG College of Technology  ·  Department of Computer Science and Engineering, Coimbatore",
    { x: X0, y: 2.9, w: CW, h: 0.4, fontSize: 14, color: G1 });

  text(s, "Under the guidance of", { x: X0, y: 3.7, w: 5, h: 0.3, fontSize: 12, color: G2 });
  text(s, "Ms. L. Karthika", { x: X0, y: 4.0, w: 5, h: 0.4, fontSize: 16, bold: true });
  text(s, "Guide", { x: X0, y: 4.38, w: 5, h: 0.3, fontSize: 11, color: G2 });
  text(s, "Dr. N. Gopika Rani", { x: X0, y: 4.85, w: 5, h: 0.4, fontSize: 16, bold: true });
  text(s, "Co-Guide", { x: X0, y: 5.23, w: 5, h: 0.3, fontSize: 11, color: G2 });

  text(s, "Team members", { x: 6.4, y: 3.7, w: 6, h: 0.3, fontSize: 12, color: G2 });
  const team = [
    ["Akhil Ramalingam", "23Z207"], ["Anbuchandiran K", "23Z209"], ["Neelesh Padmanabh", "23Z241"],
    ["Saumiyaa Sri V L", "23Z261"], ["Sowndarya Elangi S", "23Z269"], ["Therdhana J P", "23Z273"],
  ];
  team.forEach(([n, r], i) => {
    const y = 4.02 + i * 0.4;
    text(s, n, { x: 6.4, y, w: 4.2, h: 0.36, fontSize: 14 });
    text(s, r, { x: 10.6, y, w: 2.1, h: 0.36, fontSize: 14, color: G2, align: "right" });
    if (i < team.length - 1) s.addShape("line", { x: 6.4, y: y + 0.38, w: 6.33, h: 0, line: { color: G5, width: 0.5 } });
  });
}

// ============================================================ 2. PROBLEM STATEMENT
{
  const s = slide("Problem Statement");
  text(s, "Inspecting buildings, pipelines and towers is largely open-loop today:",
    { x: X0, y: 1.4, w: CW, h: 0.5, fontSize: 16, color: G1, bold: true });
  const probs = [
    ["Fixed routes", "Pre-planned path; detections never change it"],
    ["No memory", "Each flight starts from scratch; no defect tracking"],
    ["Uncertainty ignored", "Low-confidence detections trusted like confident ones; no second look"],
    ["Single-session planners", "R\u00fcckin 2023, GATSBI, Moon 2026: none tracks a defect across missions"],
  ];
  probs.forEach(([h, b], i) => {
    const x = X0 + (i % 2) * 6.17, y = 2.3 + Math.floor(i / 2) * 1.55;
    card(s, x, y, 5.96, 1.35);
    text(s, h, { x: x + 0.25, y: y + 0.18, w: 5.5, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true });
    text(s, b, { x: x + 0.25, y: y + 0.58, w: 5.5, h: 0.7, fontSize: 13, color: G1 });
  });
  text(s, "Objective", { x: X0, y: 5.45, w: 3, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true });
  bullets(s, [
    "Pick each next viewpoint from detections, uncertainty and memory",
    "Test which parts of the planner actually help",
    "Compare with published planners on the same testbed",
  ], { x: X0, y: 5.85, w: CW, h: 1.1, fontSize: 14, gap: 4 });
}

// ============================================================ 3. ABSTRACT
{
  const s = slide("Abstract");
  bullets(s, [
    "Inspection planners usually choose where to look from geometry alone",
    "UW-TIG: a closed-loop planner using detection uncertainty, defect growth (cross-mission memory), staleness and a coverage guarantee",
    "Tested against random search and five re-implemented published planners in a PyBullet yard with real defect photographs",
    "Ten seeds, two yard sizes: level with the best published planners, less flight than most",
    "The coverage guarantee and cost-aware routing carry the result; uncertainty and growth have no measurable effect",
  ], { x: X0, y: 1.4, w: CW, h: 2.8, fontSize: 15, gap: 9 });
  const tw = 2.85, tg = 0.243;
  const flyLess = Math.round(100 * (1 - TS.small.uwtig.flight / TS.small.ruckin_ipp.flight));
  [[f3(TS.small.uwtig.f1), "F1, 9-wall yard"], [f3(TS.large.uwtig.f1), "F1, 31-wall yard"],
   [f3(TS.small.uwtig_no_coverage_first.f1), "F1 without the coverage phase (9 walls)"],
   [`${flyLess}%`, "less flight than Rückin 2023 at 9 walls; F1 not significantly different"]]
    .forEach(([v, l], i) => tile(s, X0 + i * (tw + tg), 4.3, tw, 1.65, v, l));
  text(s, "Mean over 10 seeds per yard, confirmed F1, original detector", { x: X0, y: 6.05, w: CW, h: 0.3, fontSize: 11, color: G3 });
}

// ============================================================ 4. LITERATURE SURVEY
{
  const s = slide("Literature Survey (2023 - 2026)");
  const rows = [
    ["Dhami et al. (GATSBI), ICUAS 2023\nTargeted bridge inspection", "GTSP routing over target surfaces; detector added 2024", "Cost-aware and inspection-specific", "One session; no uncertainty, no memory"],
    ["Rückin et al., IEEE T-RO 2023\nInformative path planning", "Model uncertainty (MC-Dropout) drives the path", "Real learned uncertainty in planning", "One session; goal is retraining the model"],
    ["Vashisth et al., IEEE RA-L 2024\nAdaptive IPP with deep RL", "Reinforcement learning on dynamic graphs", "Learns to balance exploring and targets", "Needs training; no defect history"],
    ["Petit & Lussier Desbiens (MOAR), ICRA 2024\nRisk-aware inspection planning", "Multi-objective, risk-aware path planning", "Adapts to weather, battery and safety", "No perception or defect awareness"],
    ["Svystun et al., 2024\nWind-turbine UAV inspection", "Segmentation-guided trajectory adaptation", "78% shorter inspection time", "One structure type; no revisits"],
    ["Jin et al., 2025\nAdaptive surface inspection", "Global coverage + local reactive replanning", "Handles obstacles missing from the map", "Coverage only; no defect detection"],
    ["Moon et al. (IA-TIGRIS), IEEE T-RO 2026\nIncremental informative planning", "Sampling-based planner that reuses past plans", "Fast online replanning", "Generic information gain; no defects"],
    ["Li et al., RSS 2026\nMotion-uncertainty-aware NBV", "View selection under motion and measurement uncertainty", "Plans over uncertain futures", "Reconstruction task, not defect inspection"],
  ];
  table(s, ["Paper, authors & year", "Technique", "Advantages", "Limitations"], rows,
    { x: X0, y: 1.32, w: CW, colW: [4.0, 2.85, 2.64, 2.64], fontSize: 10.5, rowH: 0.555, leftCols: [1, 2, 3] });
}

// ============================================================ 5. GAPS & CONTRIBUTIONS
{
  const s = slide("Gaps & Contributions");
  card(s, X0, 1.4, 5.7, 4.9, "Gaps in the 2023-2026 literature");
  bullets(s, [
    "Recent planners plan for coverage or information gain, not around detected defects",
    "Single-session: a defect found last month is not tracked",
    "One scene size only: does a nine-wall planner still work on thirty?",
    "2025 reviews still list perception-driven planning as open",
  ], { x: X0 + 0.25, y: 2.25, w: 5.2, h: 3.9, fontSize: 13.5, gap: 12 });

  card(s, 6.53, 1.4, 6.2, 4.9, "Our contributions (as in the paper)");
  bullets(s, [
    { lead: "1. UW-TIG planner --", text: "coverage phase, uncertainty, growth, staleness, lookahead in one score" },
    { lead: "2. Reproducible testbed --", text: "real defect photos as textures; 9- and 31-wall yards; separate dev/test seeds" },
    { lead: "3. Evidence-first evaluation --", text: "seven planners, six ablations, ten seeds, oracle test; we report what does not matter" },
  ], { x: 6.78, y: 2.25, w: 5.75, h: 3.95, fontSize: 14, gap: 14 });
}

// ============================================================ 6. NOVELTY IN DETAIL
{
  const s = slide("Novelty in Detail: How UW-TIG Decides Where to Fly");
  s.addShape("rect", { x: X0, y: 1.3, w: CW, h: 0.58, fill: { color: CARD }, line: { color: CARD, width: 0 } });
  text(s, [
    { text: "Score of a viewpoint v:  ", options: { bold: true } },
    { text: "1.0·InfoGain(v) + 1.5·Uncertainty(v) + 2.0·Growth(v) + 1.0·Staleness(v) − 0.4·Cost(v)" },
    { text: "   (54 views re-scored after every move)", options: { color: G2 } },
  ], { x: X0 + 0.25, y: 1.3, w: CW - 0.5, h: 0.58, fontSize: 12, valign: "middle" });

  const pct = (a, b) => Math.round(100 * (1 - M(a, "total_flight_dist_m") / M(b, "total_flight_dist_m")));
  const rows = [
    ["1. Coverage guarantee",
     "See every wall once before anything else",
     "Plain information gain stopped at 4 of 9 walls",
     `F1 ${f3(TS.small.uwtig_no_coverage_first.f1)} → ${f3(TS.small.uwtig.f1)}; the decisive addition`],
    ["2. Detector uncertainty",
     "5-view TTA; spread of confidence = uncertainty",
     "Unsure detections earn a second look",
     "Shifts the route by under 1 m; no metric changes"],
    ["3. Cross-mission memory & growth",
     "Detections ray-cast to 3-D and matched (Postgres + Neo4j); growth = size change",
     "Worsening defects need tracking across flights",
     "Report after 3 looks or confidence ≥ 0.45; growth ~0 in test scenarios"],
    ["4. Staleness",
     "Priority rises with time since last view (after Alamdari)",
     "Stops fixation on one wall",
     `No staleness: F1 ${f3(TS.small.uwtig_no_staleness.f1)}, ${Math.round(100 * (1 - TS.small.uwtig_no_staleness.flight / TS.small.uwtig.flight))}% less flight`],
    ["5. Two-step lookahead",
     "Score each view with the best follow-up (weight 0.5), after Bircher",
     "Greedy choice can hit dead ends",
     `No lookahead: F1 ${f3(TS.small.uwtig_no_lookahead.f1)}, ${Math.round(100 * (1 - TS.small.uwtig_no_lookahead.flight / TS.small.uwtig.flight))}% less flight`],
  ];
  table(s, ["Component", "How it works", "Why it is needed", "Measured effect"], rows,
    { x: X0, y: 2.0, w: CW, colW: [2.15, 4.05, 2.85, 3.08], fontSize: 10.5, rowH: [0.4, 0.7, 0.7, 0.7, 0.7, 0.7], leftCols: [1, 2, 3] });
  text(s, "Ten seeds, 9-wall yard. Baseline: all new weights 0, no coverage phase, no lookahead = plain cost-normalised information gain", { x: X0, y: 6.1, w: CW, h: 0.4, fontSize: 12, color: G2 });
}

// ============================================================ 6. ARCHITECTURE
{
  const s = slide("System Architecture");
  const boxes = ["Planner", "Flight + Camera", "Detector", "Geometry", "Memory"];
  const subs = ["UW-TIG utility", "PyBullet quadrotor", "YOLOv8 + TTA", "Ray-cast to 3-D", "Postgres + Neo4j"];
  const desc = [
    "Scores 54 candidate viewpoints and picks the next one",
    "Flies there (PID physics in demo, kinematic in sweeps) and captures a frame",
    "Finds defects; 5-view TTA gives confidence and uncertainty",
    "Projects each box onto the wall plane to get a 3-D position",
    "Matches defects across missions and records growth",
  ];
  const bw = 2.05, gap = 0.47, by = 1.6, bh = 1.15;
  const cx = (i) => X0 + i * (bw + gap) + bw / 2;
  boxes.forEach((b, i) => {
    const x = X0 + i * (bw + gap);
    s.addShape("rect", { x, y: by, w: bw, h: bh, fill: { color: WHITE }, line: { color: BLACK, width: 1.5 } });
    text(s, b, { x, y: by + 0.2, w: bw, h: 0.4, fontFace: HEAD, fontSize: 15, bold: true, align: "center" });
    text(s, subs[i], { x, y: by + 0.62, w: bw, h: 0.35, fontSize: 11.5, color: G2, align: "center" });
    if (i < boxes.length - 1)
      s.addShape("line", { x: x + bw, y: by + bh / 2, w: gap, h: 0, line: { color: BLACK, width: 1.5, endArrowType: "triangle" } });
    text(s, desc[i], { x: x, y: 3.55, w: bw, h: 1.1, fontSize: 12.5, color: G1, align: "center" });
  });
  const ly = by + bh + 0.45;
  s.addShape("line", { x: cx(4), y: by + bh, w: 0, h: ly - by - bh, line: { color: G2, width: 1.25 } });
  s.addShape("line", { x: cx(0), y: ly, w: cx(4) - cx(0), h: 0, line: { color: G2, width: 1.25 } });
  s.addShape("line", { x: cx(0), y: by + bh, w: 0, h: ly - by - bh, line: { color: G2, width: 1.25, beginArrowType: "triangle" } });
  text(s, "feedback: updated coverage, uncertainty and growth drive the next choice -- and the next mission",
    { x: cx(0) + 0.2, y: ly - 0.33, w: cx(4) - cx(0) - 0.4, h: 0.3, fontSize: 11, italic: true, color: G2, align: "center" });

  card(s, X0, 5.0, CW, 1.4);
  text(s, "Test environment", { x: X0 + 0.25, y: 5.15, w: 4, h: 0.35, fontFace: HEAD, fontSize: 14, bold: true });
  bullets(s, [
    "Open-air yard: 2 buildings, pipe rack, lattice tower; 9 surfaces, 54 viewpoints",
    "Four scenarios: static, uncertain, multi-defect, growing; real MBDD2025 photos as wall textures",
  ], { x: X0 + 0.25, y: 5.55, w: CW - 0.5, h: 0.8, fontSize: 12, gap: 3 });
}

// ============================================================ 7. REQUIREMENTS, DATASET, PREPROCESSING
{
  const s = slide("Requirements, Dataset & Preprocessing");
  const cw = 3.88, g = 0.245, y = 1.4, h = 4.85;
  card(s, X0, y, cw, h, "Software requirements");
  bullets(s, [
    "Python 3.12",
    "PyBullet quadrotor simulation (PID flight)",
    "Ultralytics YOLOv8 / YOLO11, OpenCV, NumPy",
    "PostgreSQL + pgvector (detection log, identity matching)",
    "Neo4j (defect graph across missions)",
    "Docker Compose (runs both databases)",
    "NVIDIA L4 GPU (training, 31-wall sweeps)",
  ], { x: X0 + 0.25, y: y + 0.85, w: cw - 0.45, h: h - 1, fontSize: 12.5, gap: 8 });

  const x2 = X0 + cw + g;
  card(s, x2, y, cw, h, "Datasets");
  bullets(s, [
    { lead: "MBDD2025:", text: "14,471 UAV photos, 5 classes; training, test (1,448) and wall textures" },
    { lead: "dacl10k:", text: "bridge photos; 5,362 train, 810 held-out test" },
    { lead: "Roboflow corrosion:", text: "851 images added to training" },
    { lead: "Concrete-crack crops:", text: "800 held-out images; never trained on" },
    { lead: "SDNET2018:", text: "download blocked; replaced by the sets above" },
  ], { x: x2 + 0.25, y: y + 0.85, w: cw - 0.45, h: h - 1, fontSize: 12, gap: 7 });

  const x3 = x2 + cw + g;
  card(s, x3, y, cw, h, "Preprocessing");
  bullets(s, [
    { lead: "Aspect-correct crop:", text: "true wall shape at 1536 px" },
    { lead: "Square pixels:", text: "320x240 frames resampled" },
    { lead: "Oversampling:", text: "bulge images repeated ~4x" },
    { lead: "TTA ensemble:", text: "4 variants per frame give uncertainty" },
    { lead: "On-wall check:", text: "off-wall hits rejected (51-75% of false positives)" },
  ], { x: x3 + 0.25, y: y + 0.85, w: cw - 0.45, h: h - 1, fontSize: 12.5, gap: 8 });
}

// ============================================================ 8. DETECTION MODEL & EVALUATION
{
  const s = slide("Detection Model & Evaluation");
  s.addShape("rect", { x: X0, y: 1.32, w: CW, h: 0.55, fill: { color: CARD }, line: { color: CARD, width: 0 } });
  text(s, [
    { text: "Model: ", options: { bold: true } },
    { text: "YOLOv8s  ·  640 px  ·  100 epochs (L4)  ·  bulge oversampled ~4x  ·  TTA uncertainty" },
  ], { x: X0 + 0.25, y: 1.32, w: CW - 0.5, h: 0.55, fontSize: 13, valign: "middle" });

  const cls = [["Crack", 0.84, 0.75], ["Leakage", 0.90, 0.92], ["Abscission", 0.87, 0.78], ["Corrosion", 0.83, 0.79], ["Bulge", 0.95, 0.96]];
  const rows = cls.map(([c, p, r]) => [c, p.toFixed(2), r.toFixed(2), (2 * p * r / (p + r)).toFixed(2)]);
  rows.push(["Mean", "0.87", "0.84", "0.86"]);
  text(s, "Our detector -- held-out test set (1,448 images)", { x: X0, y: 2.1, w: 5.3, h: 0.3, fontSize: 12.5, bold: true });
  table(s, ["Class", "Precision", "Recall", "F1"], rows,
    { x: X0, y: 2.45, w: 5.3, colW: [2.0, 1.1, 1.1, 1.1], fontSize: 12, rowH: 0.4, boldRow: 5 });
  text(s, "mAP50 0.884  ·  mAP50-95 0.506", { x: X0, y: 5.35, w: 5.3, h: 0.35, fontSize: 13, bold: true });

  const rx = 6.25, rw = 6.48;
  text(s, "Recent detectors (2023 - 2026)", { x: rx, y: 2.1, w: rw, h: 0.3, fontSize: 12.5, bold: true });
  table(s, ["Paper", "Task / data", "P", "R", "mAP50"], [
    ["Ours (YOLOv8s)", "5 classes, public MBDD2025", "0.874", "0.842", "0.884"],
    ["Huang et al. 2025 (YOLOv11)", "Concrete crack, 1 class", "0.913", "0.766", "0.864"],
    ["Li, Shi & Sun 2026 (YOLOv11)", "Utility tunnel, private data", "0.932", "0.924", "0.926"],
    ["Inam et al. 2023 (YOLOv5m)", "Bridge crack, 1 class", "0.977", "0.967", "0.993"],
  ], { x: rx, y: 2.45, w: rw, colW: [2.35, 2.2, 0.62, 0.62, 0.69], fontSize: 11.5, rowH: 0.5, boldRow: 0, leftCols: [1] });
  bullets(s, [
    "Higher published scores come from single-class or private data; ours is 5-class on public data",
    { lead: "Extra datasets:", text: `dacl10k mAP50 ${f3(DET.old.dacl.map50)} → ${f3(DET.new.dacl.map50)}, MBDD unchanged, closed loop not improved; original detector kept` },
    { lead: "Calibration:", text: "ECE 0.29-0.33, so uncertainty only ranks views" },
  ], { x: X0, y: 5.85, w: CW, h: 1.1, fontSize: 11.5, gap: 3 });
}

// ============================================================ 9c. TEN SEEDS
{
  const s = slide("Ten Seeds, Both Yards (Corrected Statistics)");
  text(s, "Seeds 0-9, original detector, confirmed F1; 95% bootstrap CI",
    { x: X0, y: 1.3, w: CW, h: 0.4, fontSize: 13, color: G1 });
  const order = [["uwtig", "UW-TIG (ours)"], ["alamdari_latency", "Alamdari 2014"], ["gatsbi_gtsp", "GATSBI"],
    ["ruckin_ipp", "Rückin 2023"], ["random", "Random"], ["bircher_rhnbv", "Bircher 2016"], ["isler_nbv", "Isler-NBV"]];
  const rows = order.map(([p, l]) => [l, f3(TS.small[p].f1), ci3(TS.small[p].ci), f0(TS.small[p].flight),
    f3(TS.large[p].f1), ci3(TS.large[p].ci), f0(TS.large[p].flight)]);
  table(s, ["Planner", "F1 (9)", "95% CI", "m", "F1 (31)", "95% CI", "m"], rows,
    { x: X0, y: 1.85, w: 7.9, colW: [1.9, 0.9, 1.3, 0.65, 0.95, 1.3, 0.9], fontSize: 12, rowH: 0.42, boldRow: 0 });
  const ds = TS.small.ruckin_ipp.uwtig_minus, da = TS.small.alamdari_latency.uwtig_minus, dl = TS.large.alamdari_latency.uwtig_minus;
  const rx = 8.75, rw = 3.98;
  card(s, rx, 1.85, rw, 4.3, "Reading the numbers");
  bullets(s, [
    `9 walls: +${da.diff.toFixed(3)} over Alamdari (CI ${da.ci[0].toFixed(3)} to ${da.ci[1].toFixed(3)}), borderline; vs Rückin CI includes 0`,
    `31 walls: Alamdari ahead by ${(-dl.diff).toFixed(3)}, CI includes 0; it flies ${f0(TS.large.alamdari_latency.flight)} m vs ${f0(TS.large.uwtig.flight)} m`,
    "Level with the best rivals, not clearly better; flies less than most",
  ], { x: rx + 0.25, y: 2.7, w: rw - 0.45, h: 3.4, fontSize: 12, gap: 9 });
  text(s, "Replaces an earlier summary that mixed two detectors",
    { x: X0, y: 5.5, w: 7.9, h: 0.6, fontSize: 11, color: G3 });
}

// ============================================================ 9d. WHAT CARRIES THE RESULT
{
  const s = slide("What Carries the Result: Ablations, Oracle & Weights");
  const v = [["uwtig", "UW-TIG (full)"], ["uwtig_no_coverage_first", "No coverage phase"], ["uwtig_no_uncertainty", "No uncertainty term"],
    ["uwtig_no_temporal", "No growth term"], ["uwtig_no_staleness", "No staleness"], ["uwtig_no_lookahead", "No lookahead"]];
  const rows = v.map(([p, l]) => [l, f3(TS.small[p].f1), f0(TS.small[p].flight), f3(TS.large[p].f1), f0(TS.large[p].flight)]);
  table(s, ["Variant", "F1 (9)", "m", "F1 (31)", "m"], rows,
    { x: X0, y: 1.4, w: 6.4, colW: [2.4, 1.0, 0.8, 1.2, 1.0], fontSize: 12.5, rowH: 0.46, boldRow: 0 });
  text(s, "Ten seeds per yard, original detector.", { x: X0, y: 4.75, w: 6.4, h: 0.3, fontSize: 10.5, color: G3 });
  const rx = 7.3, rw = 5.43;
  card(s, rx, 1.4, rw, 4.9, "What the tests say");
  bullets(s, [
    { lead: "Coverage phase:", text: "F1 drops to 0.679 (9) and 0.658 (31) without it; it carries the result" },
    { lead: "Uncertainty and growth terms:", text: "within 0.002 of full UW-TIG" },
    { lead: "Oracle detector (perfect signals, planner-only):", text: "variants identical at 31 walls (F1 0.871 / 0.870 / 0.871)" },
    { lead: "Weights 0 / 6 / 20:", text: "F1 unchanged (9 walls 0.918 for all; 31 walls 0.822 / 0.821 / 0.820)" },
    { lead: "Staleness and lookahead:", text: "shorter flights without them; F1 0.973 at 9 walls, tied at 31" },
  ], { x: rx + 0.25, y: 2.25, w: rw - 0.5, h: 4.0, fontSize: 12, gap: 8 });
  text(s, "Uncertainty and growth terms: unsupported in these tests. The oracle is synthetic.",
    { x: X0, y: 5.2, w: 6.4, h: 1.0, fontSize: 11.5, color: G2 });
}

// ============================================================ 9e. YOLOv8 SIZE COMPARISON
{
  const s = slide("Fair Detector Comparison: YOLOv8 n / s / m");
  const Y = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "results", "detector_compare", "results.json"), "utf8"));
  const rows = [["yolov8n", "v8n"], ["yolov8s", "v8s (used)"], ["yolov8m", "v8m"]].map(([k, l]) =>
    [l, `${Y[k].params_m.toFixed(1)} M`, f3(Y[k].map50), f3(Y[k].map5095), f3(Y[k].precision), f3(Y[k].recall)]);
  table(s, ["Model", "Params", "mAP50", "mAP50-95", "Precision", "Recall"], rows,
    { x: X0, y: 1.5, w: 7.6, colW: [1.7, 1.1, 1.2, 1.3, 1.2, 1.1], fontSize: 13, rowH: 0.55, boldRow: 1 });
  bullets(s, [
    "Same 4,000-image MBDD2025 subset, 640 px, 30 epochs, batch 8, seed 0",
    "Tested on the full 1,448-image split; RTX 5060",
    "One run each; YOLOv8l not trained (8 GB GPU)",
  ], { x: X0, y: 3.9, w: 7.6, h: 1.3, fontSize: 12.5, gap: 5 });
  const rx = 8.5, rw = 4.23;
  card(s, rx, 1.5, rw, 3.6, "Reading the table");
  bullets(s, [
    `v8s adds ${(Y.yolov8s.map50 - Y.yolov8n.map50).toFixed(3)} mAP50 over v8n.`,
    `v8m adds only ${(Y.yolov8m.map50 - Y.yolov8s.map50).toFixed(3)} more for ${(Y.yolov8m.params_m / Y.yolov8s.params_m).toFixed(1)}x the parameters.`,
    "Single seed: small gaps not established",
  ], { x: rx + 0.25, y: 2.35, w: rw - 0.45, h: 2.7, fontSize: 12.5, gap: 10 });
}

// ============================================================ 9f. LIVE DEMO
{
  const s = slide("Live Demo & Recorded Flights");
  card(s, X0, 1.4, 6.5, 4.9, "Live run (PyBullet window)");
  text(s, [
    { text: "set UWTIG_MEMORY=inmem", options: { fontFace: "Courier New", breakLine: true } },
    { text: "python demo_uwtig_flight.py", options: { fontFace: "Courier New", breakLine: true } },
    { text: "    --planner uwtig --gui --missions 1", options: { fontFace: "Courier New" } },
  ], { x: X0 + 0.25, y: 2.25, w: 6.0, h: 1.0, fontSize: 12.5 });
  bullets(s, [
    "3-D window; terminal shows each wall picked and detections",
    "In-memory store: no Postgres or Docker needed.",
    "Planners to compare: uwtig, isler_nbv, random (same scene and seed).",
  ], { x: X0 + 0.25, y: 3.4, w: 6.0, h: 2.8, fontSize: 13, gap: 10 });
  card(s, 7.35, 1.4, 5.38, 4.9, "Recorded flights (output/)");
  bullets(s, [
    "Inspection view: three planners side by side",
    "3-D chase view of the same flights",
    "UW-TIG against the classical baseline",
    "One flythrough and one inspection video per planner",
  ], { x: 7.6, y: 2.25, w: 4.9, h: 3.9, fontSize: 12.5, gap: 10 });
}

// ============================================================ 10. CONCLUSION & FUTURE WORK
{
  const s = slide("Conclusion & Future Work");
  card(s, X0, 1.4, 5.95, 4.9, "Conclusion");
  bullets(s, [
    "Working closed loop: detect, assess, remember, replan",
    `UW-TIG reaches F1 ${f3(TS.small.uwtig.f1)} (9 walls) and ${f3(TS.large.uwtig.f1)} (31 walls) over ten seeds.`,
    "Level with the best published planners on ten seeds; usually less flight",
    "Coverage phase and cost-aware routing carry the result; uncertainty and growth add nothing measurable",
    "Margins shrink at scale; fine-tuned detector not adopted",
    "Design fixed on separate development seeds",
  ], { x: X0 + 0.25, y: 2.25, w: 5.45, h: 3.95, fontSize: 14, gap: 10 });

  card(s, 6.78, 1.4, 5.95, 4.9, "Future work");
  bullets(s, [
    "Raise precision in the \"uncertain\" scenario above 0.90.",
    "Find a setting where uncertainty and growth matter (weights up to 20 changed nothing)",
    "Calibrated uncertainty instead of TTA",
    "Real growth data for the growing scenario",
    "Re-implement rivals as full systems",
  ], { x: 7.03, y: 2.25, w: 5.45, h: 3.95, fontSize: 15, gap: 12 });
}

// ---------------------------------------------------------------- write
const OUT = process.env.DECK_OUT || path.join(__dirname, "..", "UW-TIG_Review_Deck.pptx");
pres.writeFile({ fileName: OUT }).then(async () => {
  const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, "-- slides:", N);
});
