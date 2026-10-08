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
pres.author = "Autonomous Drone Inspection Project";
pres.title = "Autonomous Drone Utility Inspection -- UW-TIG";

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
        text: "UW-TIG  ·  Autonomous Drone Utility Inspection",
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
  text(s, "AUTONOMOUS DRONE UTILITY INSPECTION", { x: X0, y: 0.75, w: CW, h: 0.4, fontSize: 13, bold: true, color: G2, charSpacing: 3 });
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
  text(s, "Utility infrastructure -- buildings, pipelines, towers -- needs repeated inspection for cracks, corrosion and leakage. Today's drone inspection is largely open-loop:",
    { x: X0, y: 1.4, w: CW, h: 0.7, fontSize: 15, color: G1 });
  const probs = [
    ["Fixed routes", "The drone follows a pre-planned path; what it detects never changes where it flies next."],
    ["No memory", "Every flight starts from scratch -- a defect seen last month is not tracked or compared."],
    ["Uncertainty ignored", "A low-confidence detection is treated like a confident one; nothing triggers a second look."],
    ["Geometry-only planners", "Next-best-view methods (e.g. Isler et al. 2016) maximise visual coverage, with no notion of a defect."],
  ];
  probs.forEach(([h, b], i) => {
    const x = X0 + (i % 2) * 6.17, y = 2.3 + Math.floor(i / 2) * 1.55;
    card(s, x, y, 5.96, 1.35);
    text(s, h, { x: x + 0.25, y: y + 0.18, w: 5.5, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true });
    text(s, b, { x: x + 0.25, y: y + 0.58, w: 5.5, h: 0.7, fontSize: 13, color: G1 });
  });
  text(s, "Objective", { x: X0, y: 5.55, w: 3, h: 0.35, fontFace: HEAD, fontSize: 15, bold: true });
  text(s, "Build a closed-loop drone that detects defects with a trained model, measures its own uncertainty, remembers defects across missions, and decides where to fly next -- and show it beats published planners on the same testbed.",
    { x: X0, y: 5.92, w: CW, h: 0.9, fontSize: 14 });
}

// ============================================================ 3. ABSTRACT
{
  const s = slide("Abstract");
  text(s,
    "This project builds a simulated autonomous drone (PyBullet, gym-pybullet-drones) that inspects an open-air utility yard for surface defects. " +
    "A YOLOv8 detector trained on 14,471 real UAV photographs (MBDD2025) finds cracks, leakage, abscission, corrosion and bulging, and a test-time-augmentation ensemble estimates each detection's uncertainty. " +
    "Detections are ray-cast to 3-D positions and stored in a persistent memory (PostgreSQL + pgvector, Neo4j) that tracks each defect across missions. " +
    "The proposed planner, UW-TIG, extends the information-gain next-best-view formulation of Isler et al. (2016) with a coverage guarantee, detection uncertainty, defect growth, revisit staleness and a two-step lookahead. " +
    "It is compared on held-out test seeds against random search and five re-implemented published planners.",
    { x: X0, y: 1.4, w: CW, h: 3.0, fontSize: 15, color: G1, lineSpacingMultiple: 1.15 });
  const tw = 2.85, tg = 0.243;
  [[f3(UW.p), "Precision"], [f3(UW.r), "Recall"], [f3(UW.f), "F1 score"], [`${FLY_LESS}%`, "less flight than the best published planner at equal F1"]]
    .forEach(([v, l], i) => tile(s, X0 + i * (tw + tg), 4.3, tw, 1.65, v, l));
  text(s, "Closed-loop results, mean over 3 scenarios x 5 test seeds x 3 missions", { x: X0, y: 6.05, w: CW, h: 0.3, fontSize: 11, color: G3 });
}

// ============================================================ 4. LITERATURE SURVEY
{
  const s = slide("Literature Survey");
  const rows = [
    ["Isler et al., ICRA 2016\nInformation-gain NBV (base paper)", "Entropy-based, cost-normalised next-best-view", "Principled view selection; our base formulation", "Geometry only -- no defects, no memory"],
    ["Bircher et al., ICRA 2016\nReceding-horizon NBV", "Tree search, execute first step, replan", "Plans beyond one greedy step", "Built for exploration, not defect inspection"],
    ["Alamdari, Fata & Smith, IJRR 2014\nPersistent monitoring", "Maximum-latency revisit scheduling", "Guarantees regular revisits", "Revisits by time alone; no perception"],
    ["Dhami et al. (GATSBI), 2023 / 2024\nTargeted bridge inspection", "GTSP routing + defect detector (2024)", "Cost-aware routing with a real detector", "Single session; no uncertainty, no memory"],
    ["Rückin et al., IEEE T-RO 2023\nInformative path planning", "MC-Dropout uncertainty drives the path", "Real model uncertainty guides planning", "Single session; goal is retraining the model"],
    ["Moon et al. (IA-TIGRIS), IEEE T-RO 2026\nIncremental informative planning", "Sampling-based planner, reuses past plans", "Adapts online; fixed-wing and multirotor", "Generic information gain; no defect history"],
    ["Zha et al. (MBDD2025), Scientific Data 2025\nUAV building-defect dataset", "14,471 images, 5 classes, 35 detectors benchmarked", "Large, public, real UAV defect data", "Single time-point; no growth sequences"],
  ];
  table(s, ["Paper, authors & year", "Technique", "Advantages", "Limitations"], rows,
    { x: X0, y: 1.35, w: CW, colW: [4.0, 2.75, 2.69, 2.69], fontSize: 11, rowH: 0.7, leftCols: [1, 2, 3] });
}

// ============================================================ 5. INFERENCES & NOVELTY
{
  const s = slide("Inferences & Proposed Novelty");
  card(s, X0, 1.4, 5.7, 4.9, "Inferences from the survey");
  bullets(s, [
    "Information-gain planners choose views well, but none know what a defect is.",
    "Uncertainty-driven planning exists (Rückin et al.), but only within one flight and to retrain a model.",
    "Revisit scheduling exists (Alamdari et al.), but by elapsed time, not by what was seen.",
    "No reviewed work combines detector uncertainty, memory across missions and defect growth in one planner.",
  ], { x: X0 + 0.25, y: 2.25, w: 5.2, h: 3.9, fontSize: 15, gap: 16 });

  card(s, 6.53, 1.4, 6.2, 4.9, "UW-TIG: what is new");
  bullets(s, [
    { lead: "Coverage guarantee --", text: "every wall is seen once before anything else; fixes a recall ceiling shared by the base paper." },
    { lead: "Detector uncertainty --", text: "unsure detections earn a second look (TTA ensemble of a trained YOLO model)." },
    { lead: "Cross-mission memory --", text: "Postgres + Neo4j track each defect's identity and growth over missions." },
    { lead: "Staleness --", text: "areas not seen for a while gain priority (after Alamdari et al.)." },
    { lead: "Two-step lookahead --", text: "plans one move ahead instead of pure greedy (after Bircher et al.)." },
  ], { x: 6.78, y: 2.25, w: 5.75, h: 3.95, fontSize: 14, gap: 12 });
}

// ============================================================ 6. ARCHITECTURE
{
  const s = slide("System Architecture");
  const boxes = ["Planner", "Flight + Camera", "Detector", "Geometry", "Memory"];
  const subs = ["UW-TIG utility", "PyBullet drone", "YOLOv8 + TTA", "Ray-cast to 3-D", "Postgres + Neo4j"];
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
  text(s, "Open-air utility yard: two equipment buildings plus inspection panels on a pipe rack and a lattice tower -- 9 inspectable surfaces, 54 candidate viewpoints at 1.3 m and 2.2 m standoff. Four scenarios (static, uncertain, multi-defect, growing) with real MBDD2025 photos applied as wall textures.",
    { x: X0 + 0.25, y: 5.52, w: CW - 0.5, h: 0.85, fontSize: 12.5, color: G1 });
}

// ============================================================ 7. REQUIREMENTS, DATASET, PREPROCESSING
{
  const s = slide("Requirements, Dataset & Preprocessing");
  const cw = 3.88, g = 0.245, y = 1.4, h = 4.85;
  card(s, X0, y, cw, h, "Software requirements");
  bullets(s, [
    "Python 3.12",
    "PyBullet + gym-pybullet-drones (simulation, PID flight)",
    "Ultralytics YOLOv8 / YOLO11, OpenCV, NumPy",
    "PostgreSQL + pgvector (detection log, identity matching)",
    "Neo4j (defect graph across missions)",
    "Docker Compose (runs both databases)",
    "NVIDIA L4 GPU, rented (detector training only)",
  ], { x: X0 + 0.25, y: y + 0.85, w: cw - 0.45, h: h - 1, fontSize: 12.5, gap: 8 });

  const x2 = X0 + cw + g;
  card(s, x2, y, cw, h, "Dataset");
  bullets(s, [
    { lead: "MBDD2025:", text: "14,471 real UAV photos of building surfaces (Zha et al., Scientific Data 2025)." },
    { lead: "5 classes:", text: "crack, leakage, abscission, corrosion, bulge." },
    { lead: "Split:", text: "70 / 20 / 10 train / val / test; 1,448 held-out test images." },
    { lead: "Imbalance:", text: "bulge has 2,018 instances vs. 22,702 for abscission." },
    { lead: "SDNET2018:", text: "crack augmentation planned; download pending." },
  ], { x: x2 + 0.25, y: y + 0.85, w: cw - 0.45, h: h - 1, fontSize: 12.5, gap: 8 });

  const x3 = x2 + cw + g;
  card(s, x3, y, cw, h, "Preprocessing");
  bullets(s, [
    { lead: "Aspect-correct crop:", text: "photos cropped to each wall's true shape at 1536 px (was stretched ~2.2x)." },
    { lead: "Square pixels:", text: "320x240 camera frames resampled before detection." },
    { lead: "Oversampling:", text: "bulge images repeated ~4x in training." },
    { lead: "TTA ensemble:", text: "4 photometric variants per frame give an uncertainty score." },
    { lead: "On-wall check:", text: "hits outside the wall rejected -- removed 51-75% of false positives." },
  ], { x: x3 + 0.25, y: y + 0.85, w: cw - 0.45, h: h - 1, fontSize: 12.5, gap: 8 });
}

// ============================================================ 8. DETECTION MODEL & EVALUATION
{
  const s = slide("Detection Model & Evaluation");
  card(s, X0, 1.4, 4.6, 4.75, "Model");
  bullets(s, [
    { lead: "Architecture:", text: "YOLOv8s, 640 px input" },
    { lead: "Training:", text: "100 epochs on an NVIDIA L4, bulge oversampled" },
    { lead: "Baseline:", text: "YOLOv8n, 320 px, 30 epochs on CPU -- mAP50 0.685" },
    { lead: "Uncertainty:", text: "spread of confidence across the TTA views" },
    { lead: "Retrain:", text: "YOLO11m reached mAP50 0.890 but lower precision (0.869); not yet adopted" },
  ], { x: X0 + 0.25, y: 2.25, w: 4.15, h: 3.8, fontSize: 13.5, gap: 12 });

  const cls = [["Crack", 0.84, 0.75], ["Leakage", 0.90, 0.92], ["Abscission", 0.87, 0.78], ["Corrosion", 0.83, 0.79], ["Bulge", 0.95, 0.96]];
  const rows = cls.map(([c, p, r]) => [c, p.toFixed(2), r.toFixed(2), (2 * p * r / (p + r)).toFixed(2)]);
  rows.push(["Mean (all classes)", "0.87", "0.84", "0.86"]);
  text(s, "Held-out test set: 1,448 images", { x: 5.45, y: 1.4, w: 7.3, h: 0.3, fontSize: 12, color: G2 });
  table(s, ["Class", "Precision", "Recall", "F1"], rows,
    { x: 5.45, y: 1.75, w: 7.28, colW: [2.98, 1.43, 1.43, 1.44], fontSize: 13, rowH: 0.43, boldRow: 5 });
  text(s, "mAP50 0.884   ·   mAP50-95 0.506", { x: 5.45, y: 4.85, w: 7.28, h: 0.35, fontSize: 14, bold: true });
  text(s, "Calibration check: expected calibration error is 0.29-0.33, and uncertainty is slightly lower on wrong detections than right ones -- so uncertainty is used only to rank views within a mission, never as a probability.",
    { x: 5.45, y: 5.35, w: 7.28, h: 1.3, fontSize: 12, color: G1 });
}

// ============================================================ 9. PLANNER & CLOSED-LOOP RESULTS
{
  const s = slide("UW-TIG Planner & Closed-Loop Results");
  s.addShape("rect", { x: X0, y: 1.35, w: CW, h: 0.62, fill: { color: CARD }, line: { color: CARD, width: 0 } });
  text(s, [
    { text: "Utility(v) = ", options: { bold: true } },
    { text: "1.0·InfoGain + 1.5·Uncertainty + 2.0·Growth + 1.0·Staleness − 0.4·Cost" },
    { text: "    (coverage phase first; 2-step lookahead)", options: { color: G2 } },
  ], { x: X0 + 0.25, y: 1.35, w: CW - 0.5, h: 0.62, fontSize: 14, valign: "middle", fontFace: BODY });

  const planners = [
    ["random", "Random baseline"], ["isler_nbv", "Isler et al. 2016 (base paper)"], ["bircher_rhnbv", "Bircher et al. 2016"],
    ["gatsbi_gtsp", "Dhami et al. (GATSBI)"], ["alamdari_latency", "Alamdari et al. 2014"], ["ruckin_ipp", "Rückin et al. 2023"],
    ["uwtig", "UW-TIG (ours)"],
  ].filter(([p]) => HAS(p));
  const rows = planners.map(([p, l]) => [l, f3(M(p, "precision_confirmed")), f3(M(p, "recall_confirmed")),
    f3(M(p, "f1_confirmed")), f0(M(p, "total_flight_dist_m")), f2(M(p, "coverage_frac"))]);
  table(s, ["Planner", "Precision", "Recall", "F1", "Flight (m)", "Coverage"], rows,
    { x: X0, y: 2.15, w: 7.6, colW: [2.85, 0.98, 0.95, 0.85, 1.02, 0.95], fontSize: 12, rowH: 0.42, boldRow: planners.length - 1 });

  const rx = 8.45, rw = 4.28;
  card(s, rx, 2.15, rw, 3.36, "What the results show");
  bullets(s, [
    `Ties the best published planner on F1 (${f3(UW.f)} vs ${f3(RK.f)}) while flying ${FLY_LESS}% less.`,
    `Coverage phase is decisive: F1 ${f3(M("uwtig_no_coverage_first", "f1_confirmed"))} without it.`,
    "Removing uncertainty or growth changes no metric: the coverage phase ignores both, and these scenarios have no real growth.",
    `Rückin et al. has slightly higher precision (${f3(RK.p)}).`,
  ], { x: rx + 0.25, y: 3.0, w: rw - 0.45, h: 2.45, fontSize: 12.5, gap: 8 });
  text(s, "Mean over static, uncertain and multi-defect scenarios x 5 test seeds x 3 missions; each published planner's selection rule re-implemented on the same testbed.",
    { x: X0, y: 5.6, w: 7.6, h: 0.7, fontSize: 10.5, color: G3 });
}

// ============================================================ 10. CONCLUSION & FUTURE WORK
{
  const s = slide("Conclusion & Future Work");
  card(s, X0, 1.4, 5.95, 4.9, "Conclusion");
  bullets(s, [
    `A working closed loop: detect, assess uncertainty, remember, replan, reinspect.`,
    `UW-TIG reaches precision ${f3(UW.p)}, recall ${f3(UW.r)}, F1 ${f3(UW.f)} on held-out test seeds.`,
    "Matches the strongest of five published planners on detection while flying far less.",
    "Every design choice was fixed on separate development seeds before testing.",
  ], { x: X0 + 0.25, y: 2.25, w: 5.45, h: 3.95, fontSize: 15, gap: 18 });

  card(s, 6.78, 1.4, 5.95, 4.9, "Future work");
  bullets(s, [
    `Raise the "uncertain" scenario's precision (${f3(M("uwtig", "precision_confirmed", ["uncertain"]))}) above 0.90.`,
    "Re-weight the utility so uncertainty and growth actually influence decisions.",
    "Replace TTA with a calibrated uncertainty (temperature scaling or MC-Dropout).",
    "Add real growth data so the growing-defect scenario can be detected.",
    "Re-implement published planners as full systems, not only their selection rules.",
  ], { x: 7.03, y: 2.25, w: 5.45, h: 3.95, fontSize: 15, gap: 12 });
}

// ---------------------------------------------------------------- write
const OUT = process.env.DECK_OUT || path.join(__dirname, "..", "Autonomous_Drone_Inspection_Progress.pptx");
pres.writeFile({ fileName: OUT }).then(async () => {
  const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, "-- slides:", N);
});
