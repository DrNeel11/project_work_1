const pptxgen = require("pptxgenjs");
const path = require("path");

// Pure black-on-white deck: 8 slides max, no section-divider slides, no
// filled-black callout boxes -- every slide uses the same white background /
// black text treatment.
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

const BLACK = "000000", WHITE = "FFFFFF",
  GRAY1 = "404040", GRAY2 = "595959", GRAY3 = "808080", GRAY4 = "A6A6A6", GRAY5 = "D9D9D9", GRAY6 = "F2F2F2";

const PROJECT_NAME = "Autonomous Drone Utility Inspection";

// ---------------------------------------------------------------- layout
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { placeholder: {
        options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.85,
          fontFace: THEME.headFontFace, fontSize: 28, bold: true, color: BLACK, align: "left", valign: "top" },
        text: "",
      } },
    { line: { options: { x: 0.6, y: 1.22, w: 12.1, h: 0, line: { color: BLACK, width: 1 } } } },
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
function addSlide() {
  const s = pres.addSlide({ masterName: "CONTENT" });
  s._no = ++SLIDE_NO;
  return s;
}

function title(s, text) {
  s.addText(text, { placeholder: "title" });
}

function pageFoot(s) {
  s.addText(String(s._no), { placeholder: "pageNum" });
}

// Simple numbered/bulleted list, pure black text
function bulletList(s, items, opts) {
  const o = Object.assign({ x: 0.7, y: 1.5, w: 11.9, h: 5.3, fontSize: 15 }, opts || {});
  const paras = items.map((it) => {
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

// Table: header row bold black text on white with a black rule beneath it,
// body rows alternating white / near-white for readability only.
function dataTable(s, headerRow, rows, opts) {
  const o = Object.assign({ x: 0.6, y: 1.55, w: 12.1, fontSize: 11, headerFontSize: 11.5, colW: null }, opts || {});
  const header = headerRow.map((h) => ({
    text: h,
    options: { bold: true, color: BLACK, fill: { color: WHITE }, fontSize: o.headerFontSize, align: "center", valign: "middle", fontFace: THEME.bodyFontFace, border: [{ type: "none" }, { type: "none" }, { type: "solid", color: BLACK, pt: 1.5 }, { type: "none" }] },
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
          bold: !!emph,
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

// Bordered callout (outline only, never a filled-black block)
function calloutBox(s, heading, body, opts) {
  const o = Object.assign({ x: 0.7, y: 4.4, w: 11.9, h: 1.9 }, opts || {});
  s.addShape("rect", { x: o.x, y: o.y, w: o.w, h: o.h, fill: { color: WHITE }, line: { color: BLACK, width: 1 } });
  s.addText(heading, { x: o.x + 0.25, y: o.y + 0.15, w: o.w - 0.5, h: 0.35, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 14, bold: true, color: BLACK });
  s.addText(body, { x: o.x + 0.25, y: o.y + 0.52, w: o.w - 0.5, h: o.h - 0.65, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, color: GRAY1, valign: "top" });
}

// ============================================================ SLIDE 1 -- TITLE
{
  const s = addSlide();
  s.addText("Autonomous Drone Utility Inspection", {
    x: 0.7, y: 1.7, w: 11.9, h: 1.1, isTextBox: true, margin: 0,
    fontFace: THEME.headFontFace, fontSize: 40, bold: true, color: BLACK, align: "left", valign: "top",
  });
  s.addText("UW-TIG: Uncertainty-Weighted Temporal Information Gain", {
    x: 0.7, y: 2.75, w: 11.9, h: 0.55, isTextBox: true, margin: 0,
    fontFace: THEME.bodyFontFace, fontSize: 18, color: GRAY1, align: "left",
  });
  s.addShape("line", { x: 0.7, y: 3.5, w: 6.0, h: 0, line: { color: BLACK, width: 1 } });
  s.addText(
    `UW-TIG: precision ${f3(M("uwtig", "precision_confirmed"))}  ·  recall ${f3(M("uwtig", "recall_confirmed"))}  ·  F1 ${f3(M("uwtig", "f1_confirmed"))}`,
    { x: 0.7, y: 3.75, w: 11.9, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.headFontFace, fontSize: 20, bold: true, color: BLACK }
  );
  s.addText("on held-out test seeds, measured head-to-head against five re-implemented published planners in one testbed", {
    x: 0.7, y: 4.25, w: 10.8, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 13, italic: true, color: GRAY2,
  });
  s.addText("Capstone Project -- Progress, Novelty, Literature Survey & Results", {
    x: 0.7, y: 6.7, w: 10, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12, color: GRAY3,
  });
}

// ============================================================ SLIDE 2 -- SYSTEM & DATA FLOW
{
  const s = addSlide();
  title(s, "The Gap, and the Closed-Loop System That Closes It");
  s.addText(
    "Existing NBV planners -- including the base paper -- pick viewpoints by pure geometric information gain: no defect semantics, no cross-mission memory, no validated real-detector uncertainty. This project's loop adds all three, closing on itself every mission:",
    { x: 0.6, y: 1.4, w: 12.1, h: 0.75, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 13, color: GRAY1, valign: "top" }
  );

  // ---- 5-box data-flow diagram with a looped feedback arrow ----
  const boxes = [
    "Planner\n(UW-TIG)",
    "Flight + Camera\n(PID physics /\nkinematic sim)",
    "Detector\n(YOLO +\nuncertainty)",
    "Geometry\n(ray-cast ->\n3D position)",
    "Memory\n(Postgres +\nNeo4j)",
  ];
  const bw = 1.95, bh = 1.35, gap = 0.5125, x0 = 0.6, by = 2.35;
  const centers = boxes.map((_, i) => x0 + i * (bw + gap) + bw / 2);
  boxes.forEach((label, i) => {
    const x = x0 + i * (bw + gap);
    s.addShape("rect", { x, y: by, w: bw, h: bh, fill: { color: WHITE }, line: { color: BLACK, width: 1.25 } });
    s.addText(label, { x: x + 0.08, y: by, w: bw - 0.16, h: bh, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, bold: true, color: BLACK, align: "center", valign: "middle" });
    if (i < boxes.length - 1) {
      const ax = x + bw;
      s.addShape("line", { x: ax, y: by + bh / 2, w: gap, h: 0, line: { color: BLACK, width: 1.5, endArrowType: "triangle" } });
    }
  });

  // loop-back: box5 bottom -> down -> left -> up into box1 bottom, arrow into box1
  const loopY = by + bh + 0.55;
  const lastCx = centers[centers.length - 1], firstCx = centers[0];
  s.addShape("line", { x: lastCx, y: by + bh, w: 0, h: loopY - (by + bh), line: { color: GRAY2, width: 1.25 } });
  s.addShape("line", { x: firstCx, y: loopY, w: lastCx - firstCx, h: 0, line: { color: GRAY2, width: 1.25 } });
  s.addShape("line", { x: firstCx, y: by + bh, w: 0, h: loopY - (by + bh), line: { color: GRAY2, width: 1.25, beginArrowType: "triangle" } });
  s.addText("uncertainty / growth written back into the belief -- feeds the planner's very next choice, and seeds the next mission's start", {
    x: 0.6, y: loopY + 0.1, w: 12.1, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11, italic: true, color: GRAY2, align: "center",
  });
  s.addText("9 inspectable walls/panels  ·  54 candidate viewpoints  ·  12 planners in PLANNER_REGISTRY  ·  5-seed x 4-scenario x 3-mission sweep", {
    x: 0.6, y: loopY + 0.65, w: 12.1, h: 0.4, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11, color: GRAY2, align: "center",
  });
  pageFoot(s);
}

// ============================================================ SLIDE 3 -- LITERATURE
{
  const s = addSlide();
  title(s, "Literature Survey: Where UW-TIG Sits");
  const header = ["Approach", "Uncertainty-\naware", "Cross-mission\nmemory", "Growth /\ntemporal", "Cost-\naware", "Real\ndetector", "Guarantee"];
  const rows = [
    ["Random (baseline) †", "No", "No", "No", "No", "--", "None"],
    ["Isler et al. 2016 (base paper) †", "No", "No", "No", "Yes", "--", "None stated"],
    ["Bircher et al. 2016 (RH-NBV) †", "No", "No", "No", "Yes", "--", "None stated"],
    ["Dhami et al., GATSBI †", "No", "No", "No", "Yes", "2024 only", "None stated"],
    ["Pred-NBV / MAP-NBV (Dhami et al.)", "Indirect", "No", "No", "Yes", "--", "None stated"],
    ["Liu et al. 2022 (uncertainty CPP)", "Yes", "No", "No", "Yes", "--", "Coverage bound"],
    ["Taioli et al. 2023 (POMDP/MCTS)", "Yes", "No (1 session)", "No", "Partial", "Assumed", "POMDP-optimal"],
    ["Alamdari, Fata & Smith 2014 †", "No", "Yes", "No", "Yes", "--", "O(log n) approx."],
    ["Rückin et al. 2022-23 †", "Yes", "No", "No", "Yes", "Yes", "None stated"],
    [{ text: "UW-TIG (this project)", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Yes", bold: true }, { text: "Partial*", bold: true }],
  ];
  dataTable(s, header, rows, { y: 1.35, fontSize: 10.3, headerFontSize: 10.3, rowH: 0.405, colW: [3.9, 1.5, 1.6, 1.4, 1.2, 1.3, 1.3] });
  s.addText("† Core selection rule re-implemented and measured head-to-head in this testbed.   * Inherited (1 - 1/e) greedy guarantee on the coverage sub-objective only. No cited work combines all six columns.", {
    x: 0.6, y: 5.8, w: 12.1, h: 0.35, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 10, italic: true, color: GRAY2,
  });
  s.addText("Closest relatives: GATSBI combines a real detector with cost-aware planning but has no memory or uncertainty term; Rückin et al. plan with real epistemic uncertainty in a single session, and surfaced Expected Calibration Error, a metric this project then ran on itself (next slide). Simulation stays on PyBullet -- the detector trains and evaluates only on real MBDD2025 photos as wall textures, so a game-engine renderer would not change what it learns from.", {
    x: 0.6, y: 6.2, w: 12.1, h: 0.85, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 9.3, color: GRAY3, valign: "top",
  });
  pageFoot(s);
}

// ============================================================ SLIDE 4 -- NOVELTY + ABLATIONS
{
  const s = addSlide();
  title(s, "The Novelty: Five Additions, Independently Ablated");
  const items = [
    { text: "Coverage-guarantee phase -- visits every wall once before full utility; fixes a recall ceiling that silently affected Isler-NBV too", bold: true },
    { text: "Real detector uncertainty -- TTA-ensemble variance from an actually-trained YOLO model, not an assumed oracle", bold: true },
    { text: "Persistent cross-mission memory -- Postgres + Neo4j track each defect's identity and growth across separate missions", bold: true },
    { text: "Staleness term -- revisits a spot because it hasn't been looked at in a while (Alamdari, Fata & Smith 2014)", bold: true },
    { text: "2-step receding-horizon lookahead -- plans one step ahead instead of pure greedy (Bircher et al. 2016; GATSBI)", bold: true },
  ];
  bulletList(s, items, { y: 1.4, fontSize: 12, spaceAfter: 5 });

  const header = ["Planner", "Precision", "Recall", "F1", "Loc. err (m)", "Flight (m)", "Coverage"];
  const abl = ["uwtig", "uwtig_no_uncertainty", "uwtig_no_temporal", "uwtig_no_staleness", "uwtig_no_coverage_first", "uwtig_no_lookahead"];
  const rows = abl.filter(HAS).map((p) => {
    const cells = [p === "uwtig" ? "uwtig (full)" : p, f3(M(p, "precision_confirmed")), f3(M(p, "recall_confirmed")),
      f3(M(p, "f1_confirmed")), f2(M(p, "mean_localization_error_m")), f1(M(p, "total_flight_dist_m")), f2(M(p, "coverage_frac"))];
    return p === "uwtig" ? cells.map((t) => ({ text: t, bold: true })) : cells;
  });
  dataTable(s, header, rows, { y: 3.85, fontSize: 10.5, headerFontSize: 10.8, rowH: 0.4, colW: [3.5, 1.5, 1.3, 1.2, 1.6, 1.5, 1.5] });

  const TERM = { uwtig_no_uncertainty: "the uncertainty term", uwtig_no_temporal: "the temporal term",
    uwtig_no_staleness: "the staleness term", uwtig_no_lookahead: "the lookahead", uwtig_no_coverage_first: "the coverage phase" };
  const full = M("uwtig", "f1_confirmed");
  const beats = abl.slice(1).filter((p) => HAS(p) && M(p, "f1_confirmed") > full + 1e-9);
  const note = [
    `Coverage phase is decisive: F1 ${f3(full)} with it, ${f3(M("uwtig_no_coverage_first", "f1_confirmed"))} without.`,
    beats.length ? `Removing ${beats.map((p) => TERM[p]).join(" or ")} scores slightly HIGHER and flies less -- once a single look is ~99% reliable, they add flying without adding accuracy.` : "",
  ].filter(Boolean).join(" ");
  s.addText(note, { x: 0.6, y: 6.75, w: 12.1, h: 0.6, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 10.5, italic: true, color: GRAY2, valign: "top" });
  pageFoot(s);
}

// ============================================================ SLIDE 5 -- HEAD-TO-HEAD
{
  const s = addSlide();
  title(s, "Head-to-Head vs. Published Planners");
  s.addText("Each paper's core selection rule, re-implemented in this testbed -- same detector, scenes, seeds and scoring. Mean over static / uncertain / multi-defect x 5 test seeds x 3 missions.", {
    x: 0.6, y: 1.35, w: 12.1, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, color: GRAY1, valign: "top",
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
  const lead = uw - bestF1 >= 0.02 ? `UW-TIG has the highest F1 (${f3(uw)} vs ${bestLabel} ${f3(bestF1)})`
    : uw >= bestF1 ? `UW-TIG and ${bestLabel} tie on F1 (${f3(uw)} vs ${f3(bestF1)}, inside seed noise)`
    : `${bestLabel} beats UW-TIG on F1 (${f3(bestF1)} vs ${f3(uw)})`;
  bulletList(s, [
    { text: flyLess > 0 ? `${lead} -- but UW-TIG flies ${flyLess}% less (${f1(M("uwtig", "total_flight_dist_m"))} m vs ${f1(M(best, "total_flight_dist_m"))} m).` : `${lead}.`, bold: true },
    "Faithful to each paper's selection rule, not its full system (no RRT sampling, 3D mapping or online model retraining).",
  ], { y: 1.95 + 0.46 * (rows.length + 1) + 0.25, fontSize: 12.5, spaceAfter: 8 });
  pageFoot(s);
}

// ============================================================ SLIDE 6 -- PERCEPTION + CALIBRATION
{
  const s = addSlide();
  title(s, "Perception & Calibration: Honest Numbers");
  s.addText("YOLO detectors trained on MBDD2025 (14,471 real UAV defect photos), scored on the held-out 1,448-image test set.", {
    x: 0.6, y: 1.35, w: 12.1, h: 0.35, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, color: GRAY1,
  });
  const header = ["Metric", "CPU (YOLOv8n, 320px, 30ep)", "GPU (YOLOv8s, 640px, 100ep)"];
  const rows = [
    ["mAP50", "0.685", "0.884"],
    ["Precision (mean)", "0.804", "0.874"],
    ["Recall (mean)", "0.612", "0.842"],
    ["F1", "0.695", "0.858"],
  ];
  if (DET) {
    header.push(`Retrained\n(${DET.label})`);
    const f1d = (2 * DET.p * DET.r) / (DET.p + DET.r);
    [DET.map50, DET.p, DET.r, f1d].forEach((v, i) => rows[i].push({ text: f3(v), bold: true }));
  } else {
    rows.forEach((r) => (r[2] = { text: r[2], bold: true }));
  }
  dataTable(s, header, rows, { y: 1.75, fontSize: 11.5, headerFontSize: 10.8, rowH: 0.4, colW: DET ? [3.1, 3.0, 3.0, 3.0] : [4.1, 4.0, 4.0] });

  s.addText("vs. literature: Li, Shi & Sun 2026 report 0.932 / 0.924 (private dataset, never released); Inam et al. 2023 report 0.977 / 0.967 (crack-only, strictly easier). MBDD2025 is the only fully public dataset of the three.", {
    x: 0.6, y: 3.95, w: 12.1, h: 0.5, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 10.5, color: GRAY2, valign: "top",
  });

  const calP = [...new Set(ROWS.map((r) => r.planner))];
  const eces = calP.map((p) => M(p, "ece")).filter((v) => !Number.isNaN(v));
  const gaps = calP.map((p) => M(p, "uncertainty_gap_fp_minus_tp")).filter((v) => !Number.isNaN(v));
  calloutBox(s,
    "Honest finding: is the uncertainty signal trustworthy?",
    `ECE is high (${f2(Math.min(...eces))}-${f2(Math.max(...eces))}) for every planner, well above a calibrated model's near-zero. The uncertainty gap (FP uncertainty minus TP uncertainty) is NEGATIVE for every planner (${f2(Math.min(...gaps))} to ${f2(Math.max(...gaps))}) -- the opposite of what would validate "high uncertainty means likely wrong". This doesn't invalidate the measured precision/recall (uncertainty is only a relative ranking signal, never an absolute threshold), but it is logged as a next step, not hidden.`,
    { x: 0.6, y: 4.55, w: 12.1, h: 2.2 }
  );
  pageFoot(s);
}

// ============================================================ SLIDE 7 -- VISUAL PROOF
{
  const s = addSlide();
  title(s, "Visual Proof: No Physical Drone Required");
  bulletList(s, [
    "demo_uwtig_flight.py --planner <name> flies any planner under real PID-controlled physics (gym-pybullet-drones) -- not kinematic teleport, not a fixed patrol",
    "Same scenario, same seed, same budget, three planners: UW-TIG, Isler-NBV, Random",
    "make_comparison_video.py splices frame-exact, same-timestep videos side by side",
  ], { y: 1.4, fontSize: 14, spaceAfter: 10 });
  s.addImage({ path: path.join(__dirname, "comparison_frame_bw.png"), x: 1.65, y: 3.1, w: 10.0, h: 2.5 });
  s.addShape("rect", { x: 1.65, y: 3.1, w: 10.0, h: 2.5, fill: { type: "none" }, line: { color: GRAY4, width: 0.75 } });
  s.addText("Left to right: UW-TIG, Isler-NBV, Random -- same scenario, seed, and timestep. By late mission, UW-TIG works a feature-dense real defect target while Isler-NBV is caught mid-detection on a wall the others aren't even looking at.", {
    x: 1.15, y: 5.7, w: 11.0, h: 0.8, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 11.5, italic: true, color: GRAY2, align: "center", valign: "top",
  });
  pageFoot(s);
}

// ============================================================ SLIDE 8 -- WHAT'S NEXT
{
  const s = addSlide();
  title(s, "What's Next");
  const uncP = meanOf("uwtig", "precision_confirmed", ["uncertain"]);
  const items = [
    { text: `Push the "uncertain" scenario's precision past 0.90 -- currently ${f3(uncP)}, via scenario-specific confirmation-rule tuning`, bold: false },
    { text: `Close the "growing" scenario's domain gap -- recall is ~0%; mix in synthetic training data, or get a longitudinal real dataset`, bold: false },
    ...(HAS("ruckin_ipp") ? [{ text: `Close the precision gap with Rückin et al. IPP (${f3(M("ruckin_ipp", "precision_confirmed"))} vs ${f3(M("uwtig", "precision_confirmed"))}) by re-weighting UW-TIG's utility terms`, bold: false }] : []),
    { text: "Upgrade uncertainty past TTA-ensemble variance -- prototype MC-Dropout (needs dropout spliced into YOLO's detection head + a full retrain) or try temperature scaling first", bold: false },
    { text: "Re-implement the published baselines at full-system fidelity (RRT sampling, 3D mapping, online retraining), not just the selection rule", bold: false },
    { text: "If the yolo11m GPU retrain (running now) beats the current detector, make it the default and re-run the full sweep", bold: false },
    { text: "Complete the SDNET2018 crack-class augmentation, and move toward pipeline segments and truss rigs as first-class inspectable geometry", bold: false },
  ];
  bulletList(s, items, { y: 1.4, fontSize: 13, spaceAfter: 9 });
  s.addShape("line", { x: 0.6, y: 6.15, w: 12.1, h: 0, line: { color: BLACK, width: 1 } });
  s.addText(
    `Bottom line: UW-TIG precision ${f3(M("uwtig", "precision_confirmed"))}, recall ${f3(M("uwtig", "recall_confirmed"))}, F1 ${f3(M("uwtig", "f1_confirmed"))} on held-out test seeds -- trade-offs reported plainly throughout, including where the numbers don't flatter the project.`,
    { x: 0.6, y: 6.3, w: 12.1, h: 0.7, isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, fontSize: 12, bold: true, color: BLACK, valign: "top" }
  );
  pageFoot(s);
}

// ---------------------------------------------------------------- write
const OUT = process.env.DECK_OUT || path.join(__dirname, "..", "Autonomous_Drone_Inspection_Progress.pptx");
pres.writeFile({ fileName: OUT }).then(async () => {
  const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, "-- slides:", SLIDE_NO);
});
