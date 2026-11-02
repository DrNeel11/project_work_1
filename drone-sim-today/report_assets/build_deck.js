const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

// Final-review deck. Every number is read from results/*.json so the slides
// quote the same ten-seed figures as the paper. Charts come from
// make_deck_figs.py; the other images are the simulator and paper figures.
const THEME = {
  name: "UW-TIG Review",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B1B1B", lt1: "FFFFFF", dk2: "1F3A5F", lt2: "EEF1F5",
    accent1: "1F3A5F", accent2: "A51C30", accent3: "6B7280",
    accent4: "8A8F98", accent5: "C9CED6", accent6: "3E5C86",
    hlink: "1F3A5F", folHlink: "6B7280",
  },
};

const NAVY = "1F3A5F", RED = "A51C30", INK = "1B1B1B", GREY = "6B7280", RULE = "C9CED6", WASH = "EEF1F5", WHITE = "FFFFFF";
const HEAD = THEME.headFontFace, BODY = THEME.bodyFontFace;
const X0 = 0.7, CW = 11.93; // 13.33 x 7.5 slide

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
pres.author = "UW-TIG project team";
pres.title = "UW-TIG: Closed-Loop Defect Inspection Planning";

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: WHITE },
  objects: [
    { placeholder: {
        options: { name: "title", type: "title", x: X0, y: 0.38, w: CW, h: 0.7,
          fontFace: HEAD, fontSize: 28, bold: true, color: NAVY, align: "left", valign: "middle", margin: 0 },
        text: "",
      } },
    { line: { options: { x: X0, y: 1.14, w: 0.9, h: 0, line: { color: RED, width: 3 } } } },
    { text: {
        options: { x: X0, y: 7.05, w: 8, h: 0.28, margin: 0, fontFace: BODY, fontSize: 9, color: GREY, align: "left" },
        text: "UW-TIG  |  Final review",
      } },
    { placeholder: {
        options: { name: "pageNum", type: "body", x: 12.03, y: 7.05, w: 0.6, h: 0.28, margin: 0,
          fontFace: BODY, fontSize: 9, color: GREY, align: "right", valign: "top" },
        text: "",
      } },
  ],
});

// ---------------------------------------------------------------- data
const R = (...p) => path.join(__dirname, "..", "results", ...p);
const TS = JSON.parse(fs.readFileSync(R("ten_seed_summary.json"), "utf8"));
const YO = JSON.parse(fs.readFileSync(R("detector_compare", "results.json"), "utf8"));
const FIG = (f) => path.join(__dirname, "deck_figs", f);
const ASSET = (f) => path.join(__dirname, f);
const f3 = (v) => v.toFixed(3);
const f0 = (v) => Math.round(v).toString();
const ci3 = (c) => `${c[0].toFixed(3)} to ${c[1].toFixed(3)}`;
const less = (a, b) => Math.round(100 * (1 - TS.small[a].flight / TS.small[b].flight));

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
  s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontFace: BODY, fontSize: 14, color: INK, valign: "top" }, o));
}

// One paragraph per item; plain round bullets.
function bullets(s, items, o) {
  const opt = Object.assign({ fontSize: 16, gap: 10, color: INK }, o);
  const flat = [];
  items.forEach((it) => {
    const obj = typeof it === "object" ? it : { text: it };
    const runs = obj.lead
      ? [{ text: obj.lead + " ", options: { bold: true, color: NAVY } }, { text: obj.text, options: {} }]
      : [{ text: obj.text, options: {} }];
    runs.forEach((r, i) => {
      const op = Object.assign({}, r.options);
      if (i === 0) Object.assign(op, { bullet: { indent: 18 }, paraSpaceAfter: opt.gap });
      if (i === runs.length - 1) op.breakLine = true;
      flat.push({ text: r.text, options: op });
    });
  });
  s.addText(flat, { x: opt.x, y: opt.y, w: opt.w, h: opt.h, isTextBox: true, margin: 0, fontFace: BODY,
    fontSize: opt.fontSize, color: opt.color, valign: "top" });
}

function heading(s, t, x, y, w) {
  text(s, t, { x, y, w, h: 0.4, fontFace: HEAD, fontSize: 17, bold: true, color: RED });
}

function table(s, header, rows, o) {
  const opt = Object.assign({ fontSize: 13, rowH: 0.42, boldRow: -1, leftCols: [] }, o);
  const al = (ci) => (ci === 0 || opt.leftCols.includes(ci) ? "left" : "center");
  const head = header.map((h, ci) => ({
    text: h,
    options: { bold: true, color: WHITE, fill: { color: NAVY }, fontSize: opt.fontSize, fontFace: BODY, align: al(ci), valign: "middle" },
  }));
  const body = rows.map((row, ri) => row.map((cell, ci) => ({
    text: String(cell),
    options: { color: INK, fill: { color: ri % 2 ? WASH : WHITE }, fontSize: opt.fontSize, fontFace: BODY,
      bold: ri === opt.boldRow, valign: "middle", align: al(ci) },
  })));
  s.addTable([head, ...body], { x: opt.x, y: opt.y, w: opt.w, colW: opt.colW, rowH: opt.rowH,
    border: { type: "solid", color: RULE, pt: 0.75 }, margin: [3, 7, 3, 7], autoPage: false });
}

function picture(s, file, x, y, w, h) {
  s.addImage({ path: file, x, y, w, h });
}

// ============================================================ 1. TITLE
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  N++;
  picture(s, ASSET("dissertation_figs/psg_logo.png"), 11.75, 0.45, 0.85, 1.12);
  text(s, "FINAL REVIEW  |  PROJECT WORK", { x: X0, y: 0.8, w: 9, h: 0.35, fontSize: 13, bold: true, color: GREY, charSpacing: 3 });
  text(s, "UW-TIG: Uncertainty-Weighted Temporal Information Gain for Closed-Loop Defect Inspection",
    { x: X0, y: 1.3, w: 10.6, h: 1.5, fontFace: HEAD, fontSize: 32, bold: true, color: NAVY });
  s.addShape("line", { x: X0, y: 3.0, w: 1.2, h: 0, line: { color: RED, width: 3 } });
  text(s, "PSG College of Technology, Department of Computer Science and Engineering, Coimbatore",
    { x: X0, y: 3.2, w: CW, h: 0.4, fontSize: 15, color: GREY });

  text(s, "Guide", { x: X0, y: 4.1, w: 4, h: 0.3, fontSize: 12, color: GREY });
  text(s, "Ms. L. Karthika", { x: X0, y: 4.4, w: 5, h: 0.4, fontSize: 17, bold: true });
  text(s, "Co-Guide", { x: X0, y: 5.0, w: 4, h: 0.3, fontSize: 12, color: GREY });
  text(s, "Dr. N. Gopika Rani", { x: X0, y: 5.3, w: 5, h: 0.4, fontSize: 17, bold: true });

  text(s, "Team", { x: 6.6, y: 4.1, w: 4, h: 0.3, fontSize: 12, color: GREY });
  const team = [["Akhil Ramalingam", "23Z207"], ["Anbuchandiran K", "23Z209"], ["Neelesh Padmanabh", "23Z241"],
    ["Saumiyaa Sri V L", "23Z261"], ["Sowndarya Elangi S", "23Z269"], ["Therdhana J P", "23Z273"]];
  team.forEach(([n, r], i) => {
    const y = 4.42 + i * 0.4;
    text(s, n, { x: 6.6, y, w: 3.6, h: 0.36, fontSize: 15 });
    text(s, r, { x: 10.3, y, w: 2.3, h: 0.36, fontSize: 15, color: GREY, align: "right" });
  });
}

// ============================================================ 2. PROBLEM
{
  const s = slide("Problem and objective");
  heading(s, "The problem", X0, 1.4, 6.4);
  bullets(s, [
    "Cracks, corrosion and leaks on buildings, towers and pipelines need repeated inspection",
    "Routes are usually fixed: what the camera sees never changes where it goes next",
    "Nothing carries over between flights, so a defect found last month is not tracked",
    "A low-confidence detection is trusted like a confident one",
  ], { x: X0, y: 1.85, w: 6.4, h: 2.9, fontSize: 16, gap: 9 });
  heading(s, "Objective", X0, 4.85, 6.4);
  bullets(s, [
    "Pick each next viewpoint from detections, detector uncertainty and defect memory",
    "Find out which parts of that planner actually help",
  ], { x: X0, y: 5.3, w: 6.4, h: 1.5, fontSize: 16, gap: 9 });
  picture(s, ASSET("establishing_shot.png"), 7.5, 1.5, 5.13, 3.85);
  text(s, "The simulated yard (PyBullet)", { x: 7.5, y: 5.45, w: 5.13, h: 0.3, fontSize: 11, color: GREY, align: "center" });
}

// ============================================================ 3. CONTRIBUTIONS
{
  const s = slide("Contributions");
  const items = [
    ["UW-TIG, a planner", "One score: coverage phase, uncertainty, growth, staleness, lookahead"],
    ["A reproducible testbed", "Real defect photos as textures, 9-wall and 31-wall yards, separate dev and test seeds"],
    ["An evaluation that reports what did not work", "Seven planners, six ablations, ten seeds, an oracle test; negative results included"],
  ];
  items.forEach(([h, b], i) => {
    const y = 1.6 + i * 1.75;
    text(s, String(i + 1), { x: X0, y, w: 0.8, h: 1.0, fontFace: HEAD, fontSize: 48, bold: true, color: RED });
    text(s, h, { x: X0 + 1.0, y: y + 0.02, w: 10.9, h: 0.45, fontFace: HEAD, fontSize: 20, bold: true, color: NAVY });
    text(s, b, { x: X0 + 1.0, y: y + 0.55, w: 10.6, h: 0.9, fontSize: 16, color: INK });
  });
}

// ============================================================ 4. HOW IT CHOOSES
{
  const s = slide("How UW-TIG picks the next view");
  text(s, [
    { text: "Utility(v) = ", options: { bold: true, color: NAVY } },
    { text: "1.0 InfoGain + 1.5 Uncertainty + 2.0 Growth + 1.0 Staleness − 0.4 Cost" },
  ], { x: X0, y: 1.4, w: CW, h: 0.4, fontSize: 17 });
  text(s, "54 candidate views re-scored after every move; coverage phase first",
    { x: X0, y: 1.85, w: CW, h: 0.35, fontSize: 14, color: GREY });
  const rows = [
    ["Coverage phase", "See every wall once before anything else", `F1 ${f3(TS.small.uwtig.f1)} → ${f3(TS.small.uwtig_no_coverage_first.f1)}`],
    ["Detector uncertainty", "Look again at detections the model is unsure about", "no change"],
    ["Growth from memory", "Track a defect's size across missions", "no change"],
    ["Staleness", "Revisit areas not seen for a while", `${less("uwtig_no_staleness", "uwtig")}% less flight, F1 ${f3(TS.small.uwtig_no_staleness.f1)}`],
    ["Two-step lookahead", "Score a view together with the best view after it", `${less("uwtig_no_lookahead", "uwtig")}% less flight, F1 ${f3(TS.small.uwtig_no_lookahead.f1)}`],
  ];
  table(s, ["Part", "What it does", "Effect of removing it (9 walls)"], rows,
    { x: X0, y: 2.45, w: CW, colW: [2.9, 5.4, 3.63], fontSize: 15, rowH: 0.62, leftCols: [1, 2] });
  text(s, "Ten seeds, original detector. Staleness and lookahead come from Alamdari et al. and Bircher et al.",
    { x: X0, y: 6.4, w: CW, h: 0.35, fontSize: 12, color: GREY });
}

// ============================================================ 5. SYSTEM
{
  const s = slide("System overview");
  picture(s, ASSET("paper_figs/loop.png"), X0, 1.6, 6.9, 3.5);
  bullets(s, [
    "The planner scores the candidate views after every move",
    "YOLOv8s with five-view test-time augmentation gives a detection and an uncertainty",
    "Each detection is ray-cast onto the wall and matched to known defects (Postgres and Neo4j)",
    "Defect memory feeds growth and staleness back to the planner",
    "A defect is reported after three looks, or one look at confidence 0.45 or more",
  ], { x: 8.0, y: 1.6, w: 4.65, h: 5.0, fontSize: 15, gap: 11 });
  text(s, "The same loop runs across missions, so memory persists between flights.",
    { x: X0, y: 5.3, w: 6.9, h: 0.4, fontSize: 13, color: GREY });
}

// ============================================================ 6. TEST ENVIRONMENT
{
  const s = slide("Test environment");
  picture(s, ASSET("paper_figs/yard.png"), X0, 1.45, 5.9, 4.7);
  text(s, "31-wall yard: walls in blue, candidate viewpoints in orange and red", { x: X0, y: 6.25, w: 5.9, h: 0.3, fontSize: 11, color: GREY, align: "center" });
  bullets(s, [
    { lead: "Small yard:", text: "9 walls, 54 viewpoints, budget of 16 views" },
    { lead: "Large yard:", text: "31 walls, 186 viewpoints, budget of 50 views" },
    { lead: "Scenarios:", text: "static, uncertain, multi-defect, growing" },
    { lead: "Textures:", text: "real MBDD2025 defect photographs on the walls" },
    { lead: "Seeds:", text: "development 100 to 102, test 0 to 9" },
    { lead: "Metrics:", text: "confirmed F1 and flight distance" },
  ], { x: 7.1, y: 1.5, w: 5.5, h: 5.0, fontSize: 16, gap: 12 });
}

// ============================================================ 7. DATA
{
  const s = slide("Data and detector training");
  heading(s, "Data", X0, 1.4, 5.8);
  bullets(s, [
    "MBDD2025: 14,471 UAV photos, five classes (crack, leakage, abscission, corrosion, bulge)",
    "Also tried: dacl10k bridge photos, Roboflow corrosion, concrete-crack crops",
    "Test split: 1,448 held-out MBDD2025 images",
  ], { x: X0, y: 1.85, w: 5.8, h: 3.0, fontSize: 16, gap: 10 });
  heading(s, "Preprocessing and training", 6.9, 1.4, 5.7);
  bullets(s, [
    "Photos cropped to each wall's true shape at 1536 px",
    "320x240 camera frames resampled to square pixels",
    "Bulge class oversampled about 4x",
    "Detections outside the wall are rejected, removing 51 to 75% of false positives",
    "YOLOv8s, 640 px, 100 epochs on an NVIDIA L4",
  ], { x: 6.9, y: 1.85, w: 5.7, h: 4.2, fontSize: 16, gap: 10 });
}

// ============================================================ 8. DETECTOR RESULTS
{
  const s = slide("Detector results");
  const cls = [["Crack", 0.84, 0.75], ["Leakage", 0.90, 0.92], ["Abscission", 0.87, 0.78], ["Corrosion", 0.83, 0.79], ["Bulge", 0.95, 0.96]];
  const rows = cls.map(([c, p, r]) => [c, p.toFixed(2), r.toFixed(2), (2 * p * r / (p + r)).toFixed(2)]);
  rows.push(["Mean", "0.87", "0.84", "0.86"]);
  text(s, "YOLOv8s on the held-out test split (mAP50 0.884)", { x: X0, y: 1.4, w: 5.6, h: 0.35, fontSize: 14, bold: true, color: NAVY });
  table(s, ["Class", "Precision", "Recall", "F1"], rows,
    { x: X0, y: 1.85, w: 5.6, colW: [1.9, 1.3, 1.2, 1.2], fontSize: 14, rowH: 0.45, boldRow: 5 });

  text(s, "Fair size comparison, identical settings", { x: 6.9, y: 1.4, w: 5.7, h: 0.35, fontSize: 14, bold: true, color: NAVY });
  const yrows = [["yolov8n", "v8n"], ["yolov8s", "v8s (used)"], ["yolov8m", "v8m"]].map(([k, l]) =>
    [l, `${YO[k].params_m.toFixed(1)} M`, f3(YO[k].map50), f3(YO[k].recall)]);
  table(s, ["Model", "Params", "mAP50", "Recall"], yrows,
    { x: 6.9, y: 1.85, w: 5.7, colW: [1.7, 1.3, 1.4, 1.3], fontSize: 14, rowH: 0.45, boldRow: 1 });
  text(s, "4,000-image subset, 640 px, 30 epochs, one run each. YOLOv8l was not trained (8 GB GPU).",
    { x: 6.9, y: 3.75, w: 5.7, h: 0.6, fontSize: 12, color: GREY });

  bullets(s, [
    `v8m adds only ${(YO.yolov8m.map50 - YO.yolov8s.map50).toFixed(3)} mAP50 over v8s for ${(YO.yolov8m.params_m / YO.yolov8s.params_m).toFixed(1)}x the parameters`,
    "Extra training data did not improve the closed loop, so the original detector stays the default",
    "Confidence is poorly calibrated (ECE 0.29 to 0.33), so uncertainty only ranks views",
  ], { x: X0, y: 5.4, w: CW, h: 1.5, fontSize: 15, gap: 8 });
}

// ============================================================ 9. PLANNER COMPARISON
{
  const s = slide("UW-TIG against published planners");
  picture(s, FIG("tradeoff.png"), 1.4, 1.35, 10.5, 4.27);
  const da = TS.small.alamdari_latency.uwtig_minus, dl = TS.large.alamdari_latency.uwtig_minus;
  bullets(s, [
    "Level with the best published planners on both yards, and it flies less than most of them",
    `9 walls: ahead of Alamdari by ${da.diff.toFixed(3)} (CI ${ci3(da.ci)}), borderline`,
    `31 walls: Alamdari ahead by ${(-dl.diff).toFixed(3)}, within the noise`,
  ], { x: X0, y: 5.75, w: CW, h: 1.2, fontSize: 15, gap: 5 });
}

// ============================================================ 10. WHAT CARRIES THE RESULT
{
  const s = slide("What carries the result");
  picture(s, FIG("ablation.png"), 1.4, 1.35, 10.5, 3.94);
  bullets(s, [
    `Without the coverage phase, F1 falls to ${f3(TS.small.uwtig_no_coverage_first.f1)} and ${f3(TS.large.uwtig_no_coverage_first.f1)}`,
    "Removing uncertainty or growth changes F1 by 0.002 at most, also with a perfect (oracle) detector and weights up to 20",
    "Staleness and lookahead cost extra flight but no F1",
  ], { x: X0, y: 5.45, w: CW, h: 1.5, fontSize: 15, gap: 6 });
}

// ============================================================ 11. DEMO
{
  const s = slide("Live demo");
  heading(s, "Run it", X0, 1.4, 6);
  text(s, [
    { text: "set UWTIG_MEMORY=inmem", options: { breakLine: true } },
    { text: "python demo_uwtig_flight.py --planner uwtig --gui --missions 1" },
  ], { x: X0, y: 1.9, w: 11.5, h: 0.9, fontFace: "Consolas", fontSize: 16, color: NAVY });
  bullets(s, [
    "A 3-D window shows the flight; the terminal prints each wall chosen and the detections",
    "No Postgres or Docker needed with the in-memory store",
    "Swap the planner for isler_nbv or random to compare on the same scene and seed",
  ], { x: X0, y: 3.1, w: 11.5, h: 1.8, fontSize: 16, gap: 10 });
  heading(s, "Recorded flights, if the live run is slow", X0, 5.0, 8);
  bullets(s, [
    "output/comparison_inspection_uwtig_vs_isler_nbv_vs_random.mp4 (three planners side by side)",
    "output/comparison_flythrough_uwtig_vs_isler_nbv_vs_random.mp4 (3-D chase view)",
  ], { x: X0, y: 5.45, w: 11.5, h: 1.3, fontSize: 15, gap: 8 });
}

// ============================================================ 12. CONCLUSION
{
  const s = slide("Conclusion and future work");
  heading(s, "Conclusion", X0, 1.4, 5.8);
  bullets(s, [
    "A working closed loop: detect, judge uncertainty, remember, replan",
    `F1 ${f3(TS.small.uwtig.f1)} on 9 walls and ${f3(TS.large.uwtig.f1)} on 31 walls over ten seeds`,
    "Level with the best published planners, usually with less flight",
    "The coverage phase and cost-aware routing carry the result",
    "The uncertainty and growth terms show no measurable effect",
  ], { x: X0, y: 1.85, w: 5.8, h: 4.6, fontSize: 16, gap: 12 });
  heading(s, "Future work", 6.9, 1.4, 5.7);
  bullets(s, [
    "Find a setting where uncertainty and growth matter, with real growth data",
    "A better-calibrated uncertainty than test-time augmentation",
    "Re-implement the rival planners as full systems",
    "Raise precision in the uncertain scenario above 0.90",
  ], { x: 6.9, y: 1.85, w: 5.7, h: 4.6, fontSize: 16, gap: 12 });
}

// ============================================================ 13. BACKUP TABLE
{
  const s = slide("Backup: ten-seed results");
  text(s, "Seeds 0 to 9, original detector, confirmed F1; CI is a 95% bootstrap over seeds.",
    { x: X0, y: 1.35, w: CW, h: 0.35, fontSize: 13, color: GREY });
  const order = [["uwtig", "UW-TIG"], ["alamdari_latency", "Alamdari 2014"], ["gatsbi_gtsp", "GATSBI"], ["ruckin_ipp", "Rückin 2023"],
    ["random", "Random"], ["bircher_rhnbv", "Bircher 2016"], ["isler_nbv", "Isler NBV"]];
  const c = (d) => `${d.ci[0].toFixed(3)} to ${d.ci[1].toFixed(3)}`;
  const rows = order.map(([p, l]) => [l, f3(TS.small[p].f1), c(TS.small[p]), f0(TS.small[p].flight), f3(TS.large[p].f1), c(TS.large[p]), f0(TS.large[p].flight)]);
  table(s, ["Planner", "F1 (9 walls)", "95% CI", "Flight (m)", "F1 (31 walls)", "95% CI", "Flight (m)"], rows,
    { x: X0, y: 1.85, w: CW, colW: [2.3, 1.45, 2.0, 1.3, 1.5, 2.0, 1.38], fontSize: 14, rowH: 0.5, boldRow: 0 });
}

// ---------------------------------------------------------------- write
const OUT = process.env.DECK_OUT || path.join(__dirname, "..", "UW-TIG_Review_Deck.pptx");
pres.writeFile({ fileName: OUT }).then(async () => {
  const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, "-- slides:", N);
});
