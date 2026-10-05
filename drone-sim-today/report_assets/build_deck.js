const pptxgen = require("pptxgenjs");
const path = require("path");

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
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "Autonomous Drone Inspection Project";
pres.title = "Autonomous Drone Utility Inspection -- UW-TIG";

const C = pres.SchemeColor;
const BLACK = "000000", WHITE = "FFFFFF", DARK = "1A1A1A",
  GRAY1 = "404040", GRAY2 = "595959", GRAY3 = "808080", GRAY4 = "A6A6A6", GRAY5 = "D9D9D9", GRAY6 = "F2F2F2";

const PROJECT_NAME = "Autonomous Drone Utility Inspection";

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: BLACK },
  objects: [
    { placeholder: {
        options: { name: "title", type: "title", x: 0.9, y: 2.55, w: 11.5, h: 1.5,
          fontFace: THEME.headFontFace, fontSize: 44, bold: true, color: WHITE, align: "left", valign: "bottom" },
        text: "",
      } },
    { placeholder: {
        options: { name: "subtitle", type: "body", x: 0.9, y: 4.15, w: 11.0, h: 1.0,
          fontFace: THEME.bodyFontFace, fontSize: 18, color: GRAY5, align: "left", valign: "top" },
        text: "",
      } },
  ],
});

pres.defineSlideMaster({
  title: "SECTION",
  background: { color: BLACK },
  objects: [
    { placeholder: {
        options: { name: "kicker", type: "body", x: 0.9, y: 2.5, w: 10, h: 0.6,
          fontFace: THEME.bodyFontFace, fontSize: 16, color: GRAY4, align: "left", valign: "bottom" },
        text: "",
      } },
    { placeholder: {
        options: { name: "title", type: "title", x: 0.9, y: 3.05, w: 11.0, h: 1.6,
          fontFace: THEME.headFontFace, fontSize: 40, bold: true, color: WHITE, align: "left", valign: "top" },
        text: "",
      } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { placeholder: {
        options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9,
          fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: BLACK, align: "left", valign: "top" },
        text: "",
      } },
    { text: {
        options: { name: "footer-label", x: 0.6, y: 7.12, w: 8, h: 0.3, margin: 0,
          fontFace: THEME.bodyFontFace, fontSize: 9, color: GRAY3, align: "left" },
        text: PROJECT_NAME,
      } },
    { placeholder: {
        options: { name: "pageNum", type: "body", x: 12.3, y: 7.12, w: 0.6, h: 0.3, margin: 0,
          fontFace: THEME.bodyFontFace, fontSize: 9, color: GRAY3, align: "right", valign: "top" },
        text: "",
      } },
  ],
});

// ---------------------------------------------------------------- results data
// Every closed-loop number on these slides is read from results/comparison.csv
// (written by run_full_sweep.sh), so a rebuild always matches the latest sweep.
const fs = require("fs");
const RESULTS_CSV = path.join(__dirname, "..", "results", "comparison.csv");

function loadRows(csvPath) {
  const [head, ...lines] = fs.readFileSync(csvPath, "utf8").trim().split(/\r?\n/);
  const cols = head.split(",");
  return lines.map((l) => Object.fromEntries(l.split(",").map((v, i) => [cols[i], v])));
}
const ROWS = loadRows(RESULTS_CSV);

function meanOf(planner, col, scenarios) {
  const vals = ROWS.filter((r) => r.planner === planner && scenarios.includes(r.scenario))
    .map((r) => parseFloat(r[col])).filter((v) => !Number.isNaN(v));
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : NaN;
}
const MAIN_SCEN = ["static", "uncertain", "multi_defect"]; // growing excluded, as in RESULTS.md
const M = (planner, col) => meanOf(planner, col, MAIN_SCEN);
const f2 = (v) => (Number.isNaN(v) ? "--" : v.toFixed(2));
const f3 = (v) => (Number.isNaN(v) ? "--" : v.toFixed(3));
const f1 = (v) => (Number.isNaN(v) ? "--" : v.toFixed(1));
const HAS = (p) => ROWS.some((r) => r.planner === p);

// Offline test-set metrics of a newer detector checkpoint, if one has been
// evaluated (written by hand from its `val(split="test")` output).
const DET_JSON = path.join(__dirname, "detector_metrics.json");
const DET = fs.existsSync(DET_JSON) ? JSON.parse(fs.readFileSync(DET_JSON, "utf8")) : null;
const BEST_DET = DET || { label: "YOLOv8s, 640px", p: 0.874, r: 0.842, map50: 0.884, map5095: 0.506 };

// ---------------------------------------------------------------- helpers
let SLIDE_NO = 0;
function addSlide(masterName, sectionTitle) {
  const s = pres.addSlide({ masterName, sectionTitle });
  s._no = ++SLIDE_NO;
  return s;
}

function title(s, text) {
  s.addText(text, { placeholder: "title" });
}

function footerKicker(s, text) {
  s.addText(text, {
    x: 0.6, y: 1.25, w: 12.1, h: 0.4, margin: 0, isTextBox: true,
    fontFace: THEME.bodyFontFace, fontSize: 13, italic: true, color: GRAY2, align: "left",
  });
}

// Simple numbered/bulleted list
function bulletList(s, items, opts) {
  const o = Object.assign({ x: 0.7, y: 1.5, w: 11.9, h: 5.3, fontSize: 15 }, opts || {});
  const paras = items.map((it, i) => {
    const isObj = typeof it === "object";
    const txt = isObj ? it.text : it;
    const bold = isObj && it.bold;
    const level = isObj && it.level ? it.level : 0;
    return {
      text: txt,
      options: {
        bullet: { code: level ? "2013" : "25CF", indent: 18 },
        indentLevel: level,
        fontSize: o.fontSize - level * 1,
        bold: !!bold,
        color: o.color || BLACK,
        breakLine: true,
        paraSpaceAfter: o.spaceAfter != null ? o.spaceAfter : 10,
      },
    };
  });
  s.addText(paras, { x: o.x, y: o.y, w: o.w, h: o.h, isTextBox: true, fontFace: THEME.bodyFontFace, valign: "top", margin: 0 });
}

// Table with header row shaded dark, body rows alternating white/light gray
function dataTable(s, headerRow, rows, opts) {
  const o = Object.assign({ x: 0.6, y: 1.55, w: 12.1, fontSize: 11, headerFontSize: 11.5, colW: null, boldFirstCol: false }, opts || {});
  const header = headerRow.map((h) => ({
    text: h,
    options: { bold: true, color: WHITE, fill: { color: BLACK }, fontSize: o.headerFontSize, align: "center", valign: "middle", fontFace: THEME.bodyFontFace },
  }));
  const body = rows.map((row, ri) => {
    const shade = ri % 2 === 0 ? WHITE : GRAY6;
    return row.map((cell, ci) => {
      const isObj = typeof cell === "object" && cell !== null;
      const txt = isObj ? cell.text : cell;
      const emph = isObj && cell.bold;
      return {
        text: String(txt),
        options: {
          fill: { color: isObj && cell.fill ? cell.fill : shade },
          color: BLACK,
          bold: !!emph || (o.boldFirstCol && ci === 0),
          fontSize: o.fontSize,
          align: ci === 0 ? "left" : "center",
          valign: "middle",
          fontFace: THEME.bodyFontFace,
        },
      };
    });
  });
  const tableRows = [header, ...body];
  s.addTable(tableRows, {
    x: o.x, y: o.y, w: o.w, colW: o.colW,
    border: { type: "solid", color: GRAY4, pt: 0.5 },
    autoPage: false,
    rowH: o.rowH || 0.42,
  });
}

function statRow(s, stats, opts) {
  const o = Object.assign({ x: 0.7, y: 1.6, w: 11.9, h: 1.6 }, opts || {});
  const n = stats.length;
  const cw = o.w / n;
  stats.forEach((st, i) => {
    const cx = o.x + i * cw;
    s.addShape("rect", { x: cx + 0.1, y: o.y, w: cw - 0.2, h: o.h, fill: { color: GRAY6 }, line: { color: GRAY4, width: 0.75 } });
    s.addText(st.value, {
      x: cx + 0.1, y: o.y + 0.12, w: cw - 0.2, h: o.h * 0.6, isTextBox: true, margin: 0,
      fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: BLACK, align: "center", valign: "middle",
    });
    s.addText(st.label, {
      x: cx + 0.15, y: o.y + o.h * 0.62, w: cw - 0.3, h: o.h * 0.36, isTextBox: true, margin: 0,
      fontFace: THEME.bodyFontFace, fontSize: 10.5, color: GRAY2, align: "center", valign: "top",
    });
  });
}

function pageFoot(s) {
  s.addText(String(s._no), { placeholder: "pageNum" });
}

// ============================================================ SLIDE 1 -- TITLE
{
  const s = addSlide("TITLE");
  title(s, "Autonomous Drone Utility Inspection");
  s.addText("UW-TIG: Uncertainty-Weighted Temporal Information Gain", { placeholder: "subtitle" });
  s.addText("Closed-loop perception, persistent memory, and active reinspection -- a novel planner vs. a reimplemented base paper", {
    x: 0.9, y: 5.05, w: 10.6, h: 0.6, isTextBox: true, margin: 0,
    fontFace: THEME.bodyFontFace, fontSize: 13, italic: true, color: GRAY4,
  });
  s.addText("Capstone Project -- Progress, Novelty, Literature Survey & Results", {
    x: 0.9, y: 6.6, w: 10, h: 0.4, isTextBox: true, margin: 0,
    fontFace: THEME.bodyFontFace, fontSize: 12, color: GRAY3,
  });
  // simple geometric motif: concentric circles (radar / sensing), pure B&W
  [2.1, 1.6, 1.1, 0.6].forEach((r, i) => {
    s.addShape("ellipse", { x: 10.6 - r, y: 0.75 - r + 1.9, w: r * 2, h: r * 2, fill: { type: "none" }, line: { color: i % 2 === 0 ? GRAY3 : GRAY5, width: 1.25 } });
  });
  s.addShape("ellipse", { x: 10.55, y: 2.65, w: 0.1, h: 0.1, fill: { color: WHITE }, line: { color: WHITE, width: 0 } });
}

// ============================================================ SLIDE 2 -- AGENDA
{
  const s = addSlide("CONTENT");
  title(s, "What This Deck Covers");
  const items = [
    ["01", "Problem & System", "The research gap, closed-loop architecture, what's been built"],
    ["02", "Literature Survey", "8+ planning papers, 3 simulation-engine papers, positioned precisely"],
    ["03", "The Novelty", "Five literature-grounded additions to the base paper, each independently ablated"],
    ["04", "Results", "A real 5-seed statistical sweep, perception benchmark, honest calibration check"],
    ["05", "Limitations & Future Work", "Stated plainly -- what's unresolved and what's next"],
  ];
  const top = 1.55, rowH = 1.0;
  items.forEach((it, i) => {
    const y = top + i * rowH;
    s.addShape("rect", { x: 0.7, y: y, w: 0.7, h: 0.7, fill: { color: BLACK }, line: { color: BLACK, width: 0 } });
    s.addText(it[0], { x: 0.7, y: y, w: 0.7, h: 0.7, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 20, bold: true, color: WHITE, align: "center", valign: "middle" });
    s.addText(it[1], { x: 1.65, y: y - 0.02, w: 4.6, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 17, bold: true, color: BLACK, valign: "top" });
    s.addText(it[2], { x: 1.65, y: y + 0.42, w: 10.5, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12.5, color: GRAY2, valign: "top" });
  });
  pageFoot(s);
}

// ============================================================ SECTION 1
pres.addSection({ title: "Problem & System" });
{
  const s = addSlide("SECTION", "Problem & System");
  s.addText("SECTION 1", { placeholder: "kicker" });
  s.addText("Problem & System", { placeholder: "title" });
  pageFoot(s);
}

// ---- Problem statement
{
  const s = addSlide("CONTENT", "Problem & System");
  title(s, "The Research Gap");
  bulletList(s, [
    { text: "Existing next-best-view (NBV) planners -- including the closest base paper -- pick viewpoints using pure geometric information gain", bold: false },
    { text: "They have no concept of a “defect”: geometry-only entropy, not semantic awareness", level: 1 },
    { text: "They do not persist across missions: every flight starts from a blank belief, so a growing or unresolved defect is forgotten", bold: false },
    { text: "They are not uncertainty-aware in a validated way: no real trained detector confidence feeding the plan", bold: false },
    { text: "The proposal's gap, stated precisely: a planner that combines real-detector uncertainty, persistent cross-mission memory, and cost-aware active reinspection -- validated against a real trained model, not assumed ground truth", bold: true },
  ], { fontSize: 15.5, spaceAfter: 14 });
  pageFoot(s);
}

// ---- Architecture (closed loop)
{
  const s = addSlide("CONTENT", "Problem & System");
  title(s, "The Closed Loop");
  const steps = [
    "Planner chooses a viewpoint from the current belief state",
    "Drone flies there (kinematic sim for sweeps, real PID physics for the flagship demo) and captures a frame",
    "Trained detector reports defects with confidence + epistemic uncertainty (TTA-ensemble variance)",
    "Each detection is ray-cast into a real 3D world position",
    "Reconciled against persistent memory -- matched to an existing defect or registered as new, growth computed if matched",
    "Uncertainty/growth signal is written back into the belief -- feeding the planner's very next choice, and seeded again at the next mission's start",
  ];
  const cx = 1.1, cy0 = 1.65, dy = 0.86, r = 0.22;
  steps.forEach((txt, i) => {
    const cy = cy0 + i * dy;
    s.addShape("ellipse", { x: cx - r, y: cy - r, w: r * 2, h: r * 2, fill: { color: BLACK } });
    s.addText(String(i + 1), { x: cx - r, y: cy - r, w: r * 2, h: r * 2, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11, bold: true, color: WHITE, align: "center", valign: "middle" });
    if (i < steps.length - 1) {
      s.addShape("line", { x: cx, y: cy + r, w: 0, h: dy - r * 2, line: { color: GRAY4, width: 1.25, dashType: "dash" } });
    }
    s.addText(txt, { x: cx + 0.5, y: cy - 0.28, w: 10.9, h: 0.6, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 13.5, color: BLACK, valign: "middle" });
  });
  s.addText("The loop closes on step 6: persistent memory feeds the very next decision -- not a pipeline that runs once.", {
    x: 1.1, y: cy0 + steps.length * dy - 0.1, w: 11.2, h: 0.5, isTextBox: true, margin: 0,
    fontFace: THEME.bodyFontFace, fontSize: 12.5, italic: true, color: GRAY2,
  });
  pageFoot(s);
}

// ---- Progress: what's implemented
{
  const s = addSlide("CONTENT", "Problem & System");
  title(s, "Progress: What's Been Implemented");
  const cols = [
    ["Perception", "YOLOv8 trained on MBDD2025 (14,471 real UAV photos, 5 defect classes). CPU and GPU checkpoints, both genuinely trained."],
    ["Geometry", "Every 2D detection ray-cast from the known camera pose onto the known wall plane -> real-world (x, y, z)."],
    ["Persistent Memory", "Postgres+pgvector (detection log, identity matching) + Neo4j (defect graph) -- cross-mission identity and growth."],
    ["Planning", "12 planners on one viewpoint graph: Random, the Isler-NBV base paper, 4 re-implemented literature planners (Rückin, Bircher, GATSBI, Alamdari), UW-TIG and 5 ablations."],
    ["Environment", "Open-air utility yard, 9 inspectable walls/panels, 1.3 m + 2.2 m viewpoints, real PID-controlled physics flight (gym-pybullet-drones)."],
    ["Experiments", "5-seed sweep x 4 scenarios x 12 planners x 3 missions. Every design choice fixed on separate dev seeds first."],
  ];
  const gx = 0.6, gy = 1.55, gw = 12.1, gh = 5.3, cwi = gw / 3, chi = gh / 2, pad = 0.12;
  cols.forEach((c, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = gx + col * cwi + pad, y = gy + row * chi + pad, w = cwi - 2 * pad, h = chi - 2 * pad;
    s.addShape("rect", { x, y, w, h, fill: { color: GRAY6 }, line: { color: GRAY4, width: 0.75 } });
    s.addText(c[0], { x: x + 0.18, y: y + 0.14, w: w - 0.36, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 15, bold: true, color: BLACK });
    s.addText(c[1], { x: x + 0.18, y: y + 0.56, w: w - 0.36, h: h - 0.7, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11, color: GRAY1, valign: "top" });
  });
  pageFoot(s);
}

// ============================================================ SECTION 2
pres.addSection({ title: "Literature Survey" });
{
  const s = addSlide("SECTION", "Literature Survey");
  s.addText("SECTION 2", { placeholder: "kicker" });
  s.addText("Literature Survey", { placeholder: "title" });
  pageFoot(s);
}

// ---- Base paper
{
  const s = addSlide("CONTENT", "Literature Survey");
  title(s, "The Base Paper");
  s.addText("Isler, Sabzevari, Delmerico & Scaramuzza -- “An Information Gain Formulation for Active Volumetric 3D Reconstruction” (ICRA 2016)", {
    x: 0.7, y: 1.5, w: 11.9, h: 0.6, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 14, italic: true, color: GRAY1,
  });
  bulletList(s, [
    "Entropy-based, cost-normalized information gain -- the closest prior method to this project's planner",
    "Re-implemented here (not borrowed numbers): the direct baseline UW-TIG is compared against and extends",
    "Deliberately geometry-only: no defect semantics -- the literature gap this proposal identifies",
    { text: "No precision/recall concept at all -- it is a volumetric-reconstruction quality paper, not a detection paper", bold: true },
  ], { y: 2.3, fontSize: 15.5, spaceAfter: 14 });
  pageFoot(s);
}

// ---- Literature table
{
  const s = addSlide("CONTENT", "Literature Survey");
  title(s, "Where UW-TIG Sits");
  const header = ["Approach", "Uncertainty-\naware", "Cross-mission\nmemory", "Growth /\ntemporal", "Cost-\naware", "Real\ndetector", "Guarantee"];
  const rows = [
    ["Random (baseline) †", "No", "No", "No", "No", "--", "None"],
    ["Isler et al. 2016 (base paper) †", "No", "No", "No", "Yes", "--", "None stated"],
    ["Bircher et al. 2016 (receding-horizon NBV) †", "No", "No", "No", "Yes", "--", "None stated"],
    ["Dhami et al., GATSBI (2023 / 2024) †", "No", "No", "No", "Yes", "2024 only", "None stated"],
    ["Pred-NBV / MAP-NBV (Dhami et al.)", "Indirect", "No", "No", "Yes", "--", "None stated"],
    ["Liu et al. 2022 (uncertainty-controlled CPP)", "Yes", "No", "No", "Yes", "--", "Coverage bound"],
    ["Taioli et al. 2023 (POMDP / MCTS search)", "Yes", "No (1 session)", "No", "Partial", "Assumed", "POMDP-optimal"],
    ["Alamdari, Fata & Smith 2014 (persistent monitoring) †", "No", "Yes", "No", "Yes", "--", "O(log n) approx."],
    ["Rückin et al. (ICRA'22 / IROS'22 / T-RO'23) †", "Yes", "No", "No", "Yes", "Yes", "None stated"],
    [{ text: "UW-TIG (this project)", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Partial*", bold: true }],
  ];
  dataTable(s, header, rows, { y: 1.55, fontSize: 9.3, headerFontSize: 9.8, rowH: 0.46, colW: [3.9, 1.5, 1.6, 1.4, 1.2, 1.3, 1.3] });
  s.addText("† Core selection rule re-implemented and measured head-to-head in this testbed (Results).   * Inherited (1 - 1/e) greedy guarantee on the coverage sub-objective only. No cited work combines all six columns.", {
    x: 0.6, y: 6.55, w: 12.1, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 10.5, italic: true, color: GRAY2,
  });
  pageFoot(s);
}

// ---- Closest relatives narrative
{
  const s = addSlide("CONTENT", "Literature Survey");
  title(s, "The Two Closest Relatives");
  const cw = 5.85, gap = 0.4, y0 = 1.6, h = 5.1;
  const cards = [
    { h2: "GATSBI (Dhami et al., 2023 / 2024)", body: [
      "Closest on cost-awareness: a real defect detector combined with GTSP-routed, cost-aware planning",
      "But: no persistent cross-mission memory, and no detection-uncertainty term feeding the planner",
      "Reports a “detection rate vs. frontier-exploration baseline” (11.5x better) -- a different unit than precision/recall, not directly comparable",
    ] },
    { h2: "Rückin et al. (ICRA'22 / IROS'22 / T-RO'23)", body: [
      "Closest on uncertainty: plans with real Bayesian epistemic uncertainty (BALD, MC-Dropout) normalized by cost -- structurally the same shape as UW-TIG's utility",
      "But: single-session active learning to improve a model, not persistent defect monitoring with a fixed, deployed model",
      "Surfaced a metric this project had never run on itself: Expected Calibration Error (see Results)",
    ] },
  ];
  cards.forEach((c, i) => {
    const x = 0.6 + i * (cw + gap);
    s.addShape("rect", { x, y: y0, w: cw, h, fill: { color: GRAY6 }, line: { color: GRAY4, width: 0.75 } });
    s.addText(c.h2, { x: x + 0.25, y: y0 + 0.2, w: cw - 0.5, h: 0.7, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 15, bold: true, color: BLACK, valign: "top" });
    const paras = c.body.map((t) => ({ text: t, options: { bullet: { code: "25CF", indent: 14 }, fontSize: 12.5, color: GRAY1, breakLine: true, paraSpaceAfter: 12 } }));
    s.addText(paras, { x: x + 0.25, y: y0 + 1.0, w: cw - 0.5, h: h - 1.2, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, valign: "top" });
  });
  pageFoot(s);
}

// ---- Simulation engine literature
{
  const s = addSlide("CONTENT", "Literature Survey");
  title(s, "Simulation Realism: Unity, Unreal & Beyond");
  bulletList(s, [
    { text: "AirSim (Shah, Dey, Lovett & Kapoor, FSR 2017) -- built on Unreal Engine, high-fidelity rendering + physics", bold: false },
    { text: "Flightmare (Song, Naji, Kaufmann, Loquercio & Scaramuzza, CoRL 2020) -- Unity rendering + a separate fast physics engine", bold: false },
    { text: "GRaD-Nav (Chen et al., 2025) -- the field's current frontier: 3D-Gaussian-Splatting, past rasterized game engines entirely", bold: false },
    { text: "All three solve one problem: the sim-to-real visual-fidelity gap when a model trains on rendered, synthetic imagery", bold: true },
  ], { y: 1.55, fontSize: 15, spaceAfter: 12 });
  s.addShape("rect", { x: 0.7, y: 4.35, w: 11.9, h: 2.3, fill: { color: BLACK } });
  s.addText("Why that gap doesn't apply here", { x: 1.0, y: 4.55, w: 11.3, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 15, bold: true, color: WHITE });
  s.addText(
    "This project's detector trains and is evaluated exclusively on MBDD2025's real UAV photographs applied as wall textures -- never on synthetic defect renders. The onboard camera stays tightly framed on the wall it inspects, never seeing the yard dressing. A game-engine or 3DGS renderer would make the simulator prettier to watch; it would not change a single pixel the detector learns from. PyBullet was kept -- terminal-scriptable, and gym-pybullet-drones' own PID flight stack already gives the flagship demo real (not kinematic) physics.",
    { x: 1.0, y: 4.95, w: 11.3, h: 1.6, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12, color: GRAY5, valign: "top" }
  );
  pageFoot(s);
}

// ============================================================ SECTION 3
pres.addSection({ title: "The Novelty" });
{
  const s = addSlide("SECTION", "The Novelty");
  s.addText("SECTION 3", { placeholder: "kicker" });
  s.addText("The Novelty: UW-TIG", { placeholder: "title" });
  pageFoot(s);
}

// ---- 5 additions overview
{
  const s = addSlide("CONTENT", "The Novelty");
  title(s, "Five Literature-Grounded Additions");
  const items = [
    ["0", "Coverage-guarantee phase", "Visits every wall once before switching to full utility -- fixes a recall ceiling that silently affected Isler-NBV too", "uwtig_no_coverage_first"],
    ["1", "Real detector uncertainty", "TTA-ensemble variance from an actually-trained YOLO model, not an assumed ground-truth oracle", "uwtig_no_uncertainty"],
    ["2", "Persistent cross-mission memory", "Postgres + Neo4j track each defect's identity and growth across separate missions, not just within one flight", "uwtig_no_temporal"],
    ["3", "Staleness term", "Revisits a spot purely because it hasn't been looked at in a while (Alamdari, Fata & Smith 2014)", "uwtig_no_staleness"],
    ["4", "2-step receding horizon lookahead", "Plans one step ahead instead of pure greedy (Bircher et al. 2016; GATSBI's replanning structure)", "uwtig_no_lookahead"],
  ];
  const y0 = 1.55, rh = 1.04;
  items.forEach((it, i) => {
    const y = y0 + i * rh;
    s.addShape("rect", { x: 0.7, y, w: 0.55, h: 0.55, fill: { color: BLACK } });
    s.addText(it[0], { x: 0.7, y, w: 0.55, h: 0.55, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle" });
    s.addText(it[1], { x: 1.45, y: y - 0.06, w: 5.1, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 14.5, bold: true, color: BLACK, valign: "top" });
    s.addText(it[2], { x: 1.45, y: y + 0.32, w: 7.9, h: 0.6, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11, color: GRAY1, valign: "top" });
    s.addText(it[3], { x: 9.6, y: y, w: 3.0, h: 0.55, isTextBox: true, margin: 0, fontFace: "Courier New", fontSize: 9.5, color: GRAY3, align: "right", valign: "middle" });
  });
  s.addText("Every addition is independently ablated in PLANNER_REGISTRY -- measured, not just claimed.", {
    x: 0.7, y: y0 + items.length * rh + 0.05, w: 11.9, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12.5, italic: true, color: GRAY2,
  });
  pageFoot(s);
}

// ---- Deep dive: coverage-guarantee fix
{
  const s = addSlide("CONTENT", "The Novelty");
  title(s, "Deep Dive: The Coverage-Guarantee Phase");
  s.addText("Root cause: Isler-NBV and every UW-TIG variant stalled at a fixed fraction of the walls, identically, every seed -- the cost-normalized greedy formulation itself never finds the far building worth its travel cost. No weight retune can fix that; an explicit phase does.", {
    x: 0.7, y: 1.5, w: 11.9, h: 0.9, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 13, color: GRAY1, valign: "top",
  });
  const A = "uwtig", B = "uwtig_no_coverage_first";
  statRow(s, [
    { value: `${f2(M(B, "f1_confirmed"))} → ${f2(M(A, "f1_confirmed"))}`, label: "F1 without → with the phase" },
    { value: `${f2(M(B, "recall_confirmed"))} → ${f2(M(A, "recall_confirmed"))}`, label: "Recall" },
    { value: `${f2(M(B, "coverage_frac"))} → ${f2(M(A, "coverage_frac"))}`, label: "Coverage (fraction of walls)" },
    { value: `${Math.round(M(B, "total_flight_dist_m"))} → ${Math.round(M(A, "total_flight_dist_m"))} m`, label: "Flight distance (the cost)" },
  ], { y: 2.55, h: 1.5 });
  bulletList(s, [
    "While any wall has zero visits this mission, select only among unvisited walls using Isler-NBV's own gain-minus-cost rule",
    "Once every wall has been seen, hand over to the full UW-TIG utility for reinspection",
    { text: "The single most decisive component in the final results -- the cost is more flying, stated plainly", bold: true },
  ], { y: 4.4, fontSize: 13.5, spaceAfter: 10 });
  pageFoot(s);
}

// ---- Ablation table
{
  const s = addSlide("CONTENT", "The Novelty");
  title(s, "Ablations: What Each Addition Measurably Does");
  const header = ["Planner", "Precision", "Recall", "F1", "Loc. err (m)", "Flight (m)", "Coverage"];
  const abl = ["uwtig", "uwtig_no_uncertainty", "uwtig_no_temporal", "uwtig_no_staleness", "uwtig_no_coverage_first", "uwtig_no_lookahead"];
  const rows = abl.filter(HAS).map((p) => {
    const cells = [p === "uwtig" ? "uwtig (full)" : p, f3(M(p, "precision_confirmed")), f3(M(p, "recall_confirmed")),
      f3(M(p, "f1_confirmed")), f2(M(p, "mean_localization_error_m")), f1(M(p, "total_flight_dist_m")), f2(M(p, "coverage_frac"))];
    return p === "uwtig" ? cells.map((t) => ({ text: t, bold: true })) : cells;
  });
  dataTable(s, header, rows, { y: 1.6, fontSize: 11.5, headerFontSize: 12, rowH: 0.52, colW: [3.5, 1.5, 1.3, 1.2, 1.6, 1.5, 1.5] });
  const TERM = { uwtig_no_uncertainty: "the uncertainty term", uwtig_no_temporal: "the temporal term",
    uwtig_no_staleness: "the staleness term", uwtig_no_lookahead: "the lookahead", uwtig_no_coverage_first: "the coverage phase" };
  const full = M("uwtig", "f1_confirmed");
  const beats = abl.slice(1).filter((p) => HAS(p) && M(p, "f1_confirmed") > full + 1e-9);
  const same = abl.slice(1).filter((p) => HAS(p) && Math.abs(M(p, "f1_confirmed") - full) < 5e-4);
  const note = [
    `The coverage phase is decisive: F1 ${f3(full)} with it, ${f3(M("uwtig_no_coverage_first", "f1_confirmed"))} without.`,
    beats.length ? `Stated plainly: removing ${beats.map((p) => TERM[p]).join(" or ")} scores slightly HIGHER and flies less -- once a single survey look is ~99% reliable, they add flying without adding accuracy.` : "",
    same.length ? `Removing ${same.map((p) => TERM[p]).join(" or ")} changes nothing -- in this configuration they alter no decision.` : "",
  ].filter(Boolean).join(" ");
  s.addText(note, {
    x: 0.6, y: 5.45, w: 12.1, h: 1.2, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, italic: true, color: GRAY2, valign: "top",
  });
  pageFoot(s);
}

// ============================================================ SECTION 4
pres.addSection({ title: "Results" });
{
  const s = addSlide("SECTION", "Results");
  s.addText("SECTION 4", { placeholder: "kicker" });
  s.addText("Results", { placeholder: "title" });
  pageFoot(s);
}

// ---- Perception results
{
  const s = addSlide("CONTENT", "Results");
  title(s, "Perception: Real Trained Detector");
  s.addText("YOLO detectors trained on MBDD2025 (14,471 real UAV building-defect photos), scored on the held-out test set of 1,448 images.", {
    x: 0.7, y: 1.45, w: 11.9, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 13, color: GRAY1,
  });
  const header = ["Metric", "CPU checkpoint\n(YOLOv8n, 320px, 30ep)", "GPU checkpoint\n(YOLOv8s, 640px, 100ep)"];
  const rows = [
    ["mAP50", "0.685", "0.884"],
    ["mAP50-95", "0.347", "0.506"],
    ["Precision (mean)", "0.804", "0.874"],
    ["Recall (mean)", "0.612", "0.842"],
    ["F1", "0.695", "0.858"],
  ];
  if (DET) {
    header.push(`Retrained\n(${DET.label})`);
    const f1d = (2 * DET.p * DET.r) / (DET.p + DET.r);
    [DET.map50, DET.map5095, DET.p, DET.r, f1d].forEach((v, i) => rows[i].push({ text: f3(v), bold: true }));
  } else {
    rows.forEach((r) => (r[2] = { text: r[2], bold: true }));
  }
  dataTable(s, header, rows, { y: 2.0, fontSize: 13, headerFontSize: 12, rowH: 0.5, colW: DET ? [3.1, 3.0, 3.0, 3.0] : [4.1, 4.0, 4.0] });
  bulletList(s, [
    "GPU runs trained on a rented NVIDIA L4; bulge-class oversampling (2,018 vs. abscission's 22,702 instances) addresses class imbalance",
    "Same held-out 1,448-image test set for every checkpoint -- never used for training or model selection",
  ], { y: 5.25, fontSize: 12.5, spaceAfter: 10 });
  pageFoot(s);
}

// ---- How we got above 0.90
{
  const s = addSlide("CONTENT", "Results");
  title(s, "How the Numbers Got Above 0.90: Five Real Fixes");
  s.addText("Every fix diagnosed on separate dev seeds (100-102), then frozen and run once on the reported test seeds (0-4). Each applies identically to every planner.", {
    x: 0.7, y: 1.4, w: 11.9, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12, italic: true, color: GRAY2,
  });
  const fixes = [
    ["Scoring units", "Precision divided unique true positives by every raw false-positive box -- penalizing reinspection. Now scored per inspection report."],
    ["Ground truth", "16% of MBDD2025 photos hold a second labeled defect; detecting it was counted as a false positive. Now ignored, COCO-style."],
    ["Photo distortion", "Photos were stretched ~2.2x and pixelated on the walls. Now cropped to true wall aspect at 1536 px, square-pixel frames."],
    ["Viewpoint distance", "Single-look recall: 0.47 at 0.8 m vs 0.99 at 2.2 m. The close-up tier was replaced by a 2.2 m survey tier."],
    ["Wrong-surface hits", "51-75% of false positives were on an adjacent surface, vs 1 of 1,369 true positives. Off-wall hits now rejected."],
  ];
  fixes.forEach((fx, i) => {
    const y = 1.95 + i * 0.86;
    s.addShape("rect", { x: 0.7, y, w: 0.5, h: 0.5, fill: { color: BLACK } });
    s.addText(String(i + 1), { x: 0.7, y, w: 0.5, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 16, bold: true, color: WHITE, align: "center", valign: "middle" });
    s.addText(fx[0], { x: 1.4, y: y - 0.04, w: 2.6, h: 0.6, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 14, bold: true, color: BLACK, valign: "top" });
    s.addText(fx[1], { x: 4.1, y: y - 0.04, w: 8.5, h: 0.75, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12, color: GRAY1, valign: "top" });
  });
  s.addText(`Report rule (chosen on dev by planner-averaged F1): a defect is reported once seen in 3 looks across missions, or once at confidence ≥ 0.45. UW-TIG: 0.76 / 0.63 / 0.65 before → ${f2(M("uwtig", "precision_confirmed"))} / ${f2(M("uwtig", "recall_confirmed"))} / ${f2(M("uwtig", "f1_confirmed"))} now.`, {
    x: 0.7, y: 6.3, w: 11.9, h: 0.6, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12, bold: true, color: BLACK, valign: "top",
  });
  pageFoot(s);
}

// ---- Multi-paper closed-loop comparison
{
  const s = addSlide("CONTENT", "Results");
  title(s, "Head-to-Head vs. Published Planners");
  s.addText("Each paper's core selection rule, re-implemented in this testbed -- same detector, scenes, seeds and scoring. Mean over static / uncertain / multi-defect x 5 test seeds x 3 missions.", {
    x: 0.7, y: 1.35, w: 11.9, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, color: GRAY1, valign: "top",
  });
  const planners = [
    ["random", "Random baseline"],
    ["isler_nbv", "Isler et al. 2016 (base paper)"],
    ["bircher_rhnbv", "Bircher et al. 2016 (RH-NBV)"],
    ["gatsbi_gtsp", "Dhami et al., GATSBI"],
    ["ruckin_ipp", "Rückin et al. 2023 (IPP)"],
    ["alamdari_latency", "Alamdari et al. 2014 (latency)"],
    ["uwtig", "UW-TIG (this project)"],
  ].filter(([p]) => HAS(p));
  const header = ["Planner", "Precision", "Recall", "F1", "F1 single-look", "Loc. err (m)", "Flight (m)", "Coverage"];
  const rows = planners.map(([p, label]) => {
    const cells = [label, f3(M(p, "precision_confirmed")), f3(M(p, "recall_confirmed")), f3(M(p, "f1_confirmed")),
      f3(M(p, "f1")), f2(M(p, "mean_localization_error_m")), f1(M(p, "total_flight_dist_m")), f2(M(p, "coverage_frac"))];
    return p === "uwtig" ? cells.map((t) => ({ text: t, bold: true })) : cells;
  });
  dataTable(s, header, rows, { y: 1.95, fontSize: 11, headerFontSize: 11, rowH: 0.46, colW: [3.4, 1.2, 1.1, 1.0, 1.4, 1.3, 1.3, 1.4] });
  const others = planners.map(([p]) => p).filter((p) => p !== "uwtig");
  const best = others.reduce((a, b) => (M(b, "f1_confirmed") > M(a, "f1_confirmed") ? b : a), others[0]);
  const bestLabel = planners.find(([p]) => p === best)[1];
  const uw = M("uwtig", "f1_confirmed");
  const bestF1 = M(best, "f1_confirmed");
  const flyLess = Math.round(100 * (1 - M("uwtig", "total_flight_dist_m") / M(best, "total_flight_dist_m")));
  // A lead under 0.02 F1 is inside this sweep's seed-to-seed spread -- call it a tie.
  const lead = uw - bestF1 >= 0.02 ? `UW-TIG has the highest F1 (${f3(uw)} vs ${bestLabel} ${f3(bestF1)})`
    : uw >= bestF1 ? `UW-TIG and ${bestLabel} tie on F1 (${f3(uw)} vs ${f3(bestF1)}, inside seed noise)`
    : `${bestLabel} beats UW-TIG on F1 (${f3(bestF1)} vs ${f3(uw)})`;
  bulletList(s, [
    { text: flyLess > 0 ? `${lead} -- but UW-TIG flies ${flyLess}% less (${f1(M("uwtig", "total_flight_dist_m"))} m vs ${f1(M(best, "total_flight_dist_m"))} m).` : `${lead}.`, bold: true },
    "Faithful to each paper's selection rule, not its full system (no RRT sampling, 3D mapping or online model retraining).",
  ], { y: 1.95 + 0.46 * (rows.length + 1) + 0.25, fontSize: 12.5, spaceAfter: 8 });
  pageFoot(s);
}

// ---- Calibration findings
{
  const s = addSlide("CONTENT", "Results");
  title(s, "Honest Finding: Is the Uncertainty Signal Trustworthy?");
  const calP = [...new Set(ROWS.map((r) => r.planner))];
  const eces = calP.map((p) => M(p, "ece")).filter((v) => !Number.isNaN(v));
  const gaps = calP.map((p) => M(p, "uncertainty_gap_fp_minus_tp")).filter((v) => !Number.isNaN(v));
  bulletList(s, [
    "Reading Rückin et al.'s evaluation methodology prompted a check this project had never run on itself, despite its name: Expected Calibration Error",
    { text: `ECE is high (${f2(Math.min(...eces))}–${f2(Math.max(...eces))}) for every planner -- well above a calibrated model's near-zero`, bold: true },
    { text: `The uncertainty gap (FP uncertainty minus TP uncertainty) is ${Math.max(...gaps) < 0 ? "NEGATIVE for every planner" : "mixed across planners"} (${f2(Math.min(...gaps))} to ${f2(Math.max(...gaps))})`, bold: true },
    "That's the opposite of what would validate “high uncertainty means likely wrong” -- and it still holds after the >0.90 fixes",
  ], { y: 1.55, fontSize: 14.5, spaceAfter: 12 });
  s.addShape("rect", { x: 0.7, y: 4.1, w: 11.9, h: 2.55, fill: { color: BLACK } });
  s.addText("Stated plainly, not hidden", { x: 1.0, y: 4.3, w: 11.3, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 15, bold: true, color: WHITE });
  s.addText(
    "This doesn't invalidate the planner's measured precision/recall results -- uncertainty is used only as a relative ranking signal within one mission, never thresholded as an absolute probability. But it does mean this project cannot currently back the claim that high TTA-uncertainty means a detection is probably wrong. A real fix: swap in an uncertainty estimate validated for calibration (e.g. MC-Dropout, or post-hoc temperature scaling) -- logged as future work, not papered over.",
    { x: 1.0, y: 4.75, w: 11.3, h: 1.75, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12.5, color: GRAY5, valign: "top" }
  );
  pageFoot(s);
}

// ---- Cross-paper detector comparison
{
  const s = addSlide("CONTENT", "Results");
  title(s, "Honest Comparison: This Detector vs. the Literature");
  const header = ["Source", "Task", "Dataset", "Precision", "Recall", "mAP"];
  const rows = [
    [{ text: `This project (${BEST_DET.label})`, bold: true }, "5-class UAV defect detection", "MBDD2025 -- public, 14,471 photos", { text: f3(BEST_DET.p), bold: true }, { text: f3(BEST_DET.r), bold: true }, { text: f3(BEST_DET.map50), bold: true }],
    ["Li, Shi & Sun 2026", "Utility-tunnel defect detection", "Private, 5,000 images -- never released", "0.932", "0.924", "0.926"],
    ["Inam et al. 2023 (best variant)", "Bridge crack only (1 class)", "Own field data + SDNET2018", "0.977", "0.967", "0.993"],
  ];
  dataTable(s, header, rows, { y: 1.55, fontSize: 12.5, headerFontSize: 12.5, rowH: 0.62, colW: [2.9, 3.0, 3.3, 1.0, 1.0, 1.0] });
  bulletList(s, [
    { text: BEST_DET.map50 < 0.926 ? "This project's numbers are lower -- stated plainly, not explained away"
      : "This project's mAP is now in the same range -- on a harder 5-class task and a fully public dataset", bold: true },
    "But the comparison cuts both ways: Inam et al.'s number is crack-only (strictly easier, no cross-class confusion); Li et al.'s dataset is private and unverifiable",
    "MBDD2025 is the only fully public, independently reproducible dataset of the three",
    "The controlled claim this project rests on is the same-testbed head-to-head comparison, not a claim of leading the wider literature on raw detector numbers",
  ], { y: 4.35, fontSize: 13, spaceAfter: 10 });
  pageFoot(s);
}

// ---- Visual proof
{
  const s = addSlide("CONTENT", "Results");
  title(s, "Visual Proof: No Physical Drone Required");
  bulletList(s, [
    "demo_uwtig_flight.py --planner <name> flies any planner under real PID-controlled physics (gym-pybullet-drones) -- not kinematic teleport, not a fixed patrol",
    "Same scenario, same seed, same budget, three planners: UW-TIG, Isler-NBV, Random",
    "make_comparison_video.py splices frame-exact, same-timestep videos side by side",
  ], { y: 1.5, fontSize: 14, spaceAfter: 10 });
  s.addImage({ path: path.join(__dirname, "comparison_frame_bw.png"), x: 1.65, y: 3.2, w: 10.0, h: 2.5 });
  s.addShape("rect", { x: 1.65, y: 3.2, w: 10.0, h: 2.5, fill: { type: "none" }, line: { color: GRAY4, width: 0.75 } });
  s.addText("Left to right: UW-TIG, Isler-NBV, Random -- same scenario, seed, and timestep. Each already at a different wall. By late mission, UW-TIG works a feature-dense real defect target while Isler-NBV is caught mid-detection on a wall the others aren't even looking at.", {
    x: 1.15, y: 5.78, w: 11.0, h: 0.8, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, italic: true, color: GRAY2, align: "center", valign: "top",
  });
  pageFoot(s);
}

// ============================================================ SECTION 5
pres.addSection({ title: "Limitations & Future Work" });
{
  const s = addSlide("SECTION", "Limitations & Future Work");
  s.addText("SECTION 5", { placeholder: "kicker" });
  s.addText("Limitations & Future Work", { placeholder: "title" });
  pageFoot(s);
}

// ---- Limitations
{
  const s = addSlide("CONTENT", "Limitations & Future Work");
  title(s, "Limitations, Stated Plainly");
  const uncP = meanOf("uwtig", "precision_confirmed", ["uncertain"]);
  bulletList(s, [
    { text: `Averages clear 0.90, the floor does not: the faint “uncertain” scenario's precision is ${f3(uncP)}`, bold: true },
    { text: "The “growing” scenario's recall is ~0% -- a synthetic texture the real-photo detector doesn't recognize", bold: true },
    { text: "Part of the gain is measurement, not planning: the scoring and geometry fixes lifted every planner", bold: true },
    { text: "The old scoring formula on these same runs gives UW-TIG precision " + f3(M("uwtig", "precision_legacy")), level: 1 },
    { text: "Literature planners are re-implemented at the selection-rule level, not as full systems", bold: true },
    ...(HAS("ruckin_ipp") ? [{ text: "UW-TIG's edge over the best published rule is flight cost, not detection quality", bold: true },
      { text: `Rückin et al. IPP: F1 ${f3(M("ruckin_ipp", "f1_confirmed"))} vs ${f3(M("uwtig", "f1_confirmed"))}, and higher precision (${f3(M("ruckin_ipp", "precision_confirmed"))} vs ${f3(M("uwtig", "precision_confirmed"))})`, level: 1 }] : []),
    { text: "Uncertainty is TTA-ensemble variance (not MC-Dropout), poorly calibrated, and its gap is negative", bold: true },
  ], { y: 1.55, fontSize: 14, spaceAfter: 9 });
  pageFoot(s);
}

// ---- Future work
{
  const s = addSlide("CONTENT", "Limitations & Future Work");
  title(s, "Further Work");
  const items = [
    "Decide whether staleness and lookahead stay on by default -- their ablations now match or beat the full planner",
    "Raise the “uncertain” scenario's precision above 0.90 -- the one slice still below the target",
    "Close the growing-scenario domain gap -- mix in synthetic defect imagery, or acquire a longitudinal real dataset",
    "Re-implement the literature baselines at full-system fidelity (RRT sampling, 3D mapping, online retraining)",
    "Replace TTA-ensemble variance with a calibration-validated uncertainty estimate -- MC-Dropout, or temperature scaling",
    "Complete the SDNET2018 crack-class augmentation (converter built, download pending)",
    "Move toward pipeline segments and truss rigs as first-class inspectable geometry",
  ];
  bulletList(s, items, { y: 1.55, fontSize: 14, spaceAfter: 13 });
  pageFoot(s);
}

// ============================================================ CLOSE
{
  const s = addSlide("SECTION");
  s.addText("IN SUMMARY", { placeholder: "kicker" });
  s.addText("A Real Closed Loop, Validated Honestly", { placeholder: "title" });
  s.addText(
    `UW-TIG: precision ${f3(M("uwtig", "precision_confirmed"))}, recall ${f3(M("uwtig", "recall_confirmed"))}, F1 ${f3(M("uwtig", "f1_confirmed"))} on held-out test seeds --\nmeasured head-to-head against re-implementations of five published planners in one testbed.\nTrade-offs reported plainly, including where the numbers don't flatter the project.`,
    { x: 0.9, y: 4.85, w: 11.3, h: 1.5, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 14, color: GRAY5, valign: "top", lineSpacingMultiple: 1.3 }
  );
  pageFoot(s);
}

// ---------------------------------------------------------------- write
const OUT = process.env.DECK_OUT || path.join(__dirname, "..", "Autonomous_Drone_Inspection_Progress.pptx");
pres.writeFile({ fileName: OUT }).then(async () => {
  const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
});
