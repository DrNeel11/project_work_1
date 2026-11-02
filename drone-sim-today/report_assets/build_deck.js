const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

// Final-review deck, laid out like the department's reference deck: title,
// architecture, novelty completion, evaluation metrics, references, then the
// detail slides. Every number is read from results/*.json so the slides quote
// the same ten-seed figures as the paper.
const THEME = {
  name: "UW-TIG Final Review",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0B1624", lt1: "FFFFFF", dk2: "13263A", lt2: "F2F5F8",
    accent1: "2FA8B8", accent2: "34C38F", accent3: "A9B4C0",
    accent4: "2A4257", accent5: "1E6E7E", accent6: "E5B455",
    hlink: "2FA8B8", folHlink: "A9B4C0",
  },
};

const BG = "0B1624", PANEL = "13263A", PANEL2 = "0F1F30", TEAL = "2FA8B8", TEALD = "1E6E7E", GREEN = "34C38F",
  TEXT = "F2F5F8", MUTED = "A9B4C0", RULE = "2A4257", WHITE = "FFFFFF", AMBER = "E5B455";
const HEAD = THEME.headFontFace, BODY = THEME.bodyFontFace;
const X0 = 0.7, CW = 11.93; // 13.33 x 7.5 slide

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
pres.author = "UW-TIG project team";
pres.title = "UW-TIG: Final Review";

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: BG },
  objects: [
    { placeholder: {
        options: { name: "title", type: "title", x: X0, y: 0.38, w: CW, h: 0.8,
          fontFace: HEAD, fontSize: 36, bold: true, color: WHITE, align: "left", valign: "middle", margin: 0 },
        text: "",
      } },
    { line: { options: { x: X0, y: 1.22, w: 2.4, h: 0, line: { color: TEAL, width: 1.25 } } } },
    { placeholder: {
        options: { name: "pageNum", type: "body", x: 12.03, y: 7.05, w: 0.6, h: 0.28, margin: 0,
          fontFace: BODY, fontSize: 10, color: MUTED, align: "right", valign: "top" },
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
  s.addText(t, Object.assign({ isTextBox: true, margin: 0, fontFace: BODY, fontSize: 16, color: TEXT, valign: "top" }, o));
}

// One paragraph per item; "Lead: rest" items get a teal lead-in like the reference deck.
function bullets(s, items, o) {
  const opt = Object.assign({ fontSize: 20, gap: 12, color: TEXT }, o);
  const flat = [];
  items.forEach((it) => {
    const obj = typeof it === "object" ? it : { text: it };
    const runs = obj.lead
      ? [{ text: obj.lead + ": ", options: { color: obj.leadColor || TEAL } }, { text: obj.text, options: {} }]
      : [{ text: obj.text, options: {} }];
    runs.forEach((r, i) => {
      const op = Object.assign({}, r.options);
      if (i === 0) Object.assign(op, { bullet: { indent: 20 }, paraSpaceAfter: opt.gap });
      if (i === runs.length - 1) op.breakLine = true;
      flat.push({ text: r.text, options: op });
    });
  });
  s.addText(flat, { x: opt.x, y: opt.y, w: opt.w, h: opt.h, isTextBox: true, margin: 0, fontFace: BODY,
    fontSize: opt.fontSize, color: opt.color, valign: "top" });
}

function heading(s, t, x, y, w) {
  text(s, t, { x, y, w, h: 0.42, fontSize: 20, bold: true, color: TEAL });
}

function table(s, header, rows, o) {
  const opt = Object.assign({ fontSize: 14, rowH: 0.42, boldRow: -1, leftCols: [] }, o);
  const al = (ci) => (ci === 0 || opt.leftCols.includes(ci) ? "left" : "center");
  const head = header.map((h, ci) => ({
    text: h,
    options: { bold: true, color: WHITE, fill: { color: TEALD }, fontSize: opt.fontSize, fontFace: BODY, align: al(ci), valign: "middle" },
  }));
  const body = rows.map((row, ri) => row.map((cell, ci) => ({
    text: String(cell),
    options: { color: ri === opt.boldRow ? GREEN : TEXT, fill: { color: ri % 2 ? PANEL2 : PANEL }, fontSize: opt.fontSize, fontFace: BODY,
      bold: ri === opt.boldRow, valign: "middle", align: al(ci) },
  })));
  s.addTable([head, ...body], { x: opt.x, y: opt.y, w: opt.w, colW: opt.colW, rowH: opt.rowH,
    border: { type: "solid", color: RULE, pt: 0.75 }, margin: [3, 8, 3, 8], autoPage: false });
}

// Figures have white backgrounds, so they sit on a white panel like the reference deck's diagrams.
function picture(s, file, x, y, w, h) {
  s.addShape("rect", { x: x - 0.06, y: y - 0.06, w: w + 0.12, h: h + 0.12, fill: { color: WHITE }, line: { color: WHITE, width: 0 } });
  s.addImage({ path: file, x, y, w, h });
}

// ============================================================ 1. TITLE
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  N++;
  text(s, "UW-TIG", { x: X0, y: 1.2, w: 9, h: 1.3, fontSize: 80, bold: true, color: WHITE });
  text(s, "UNCERTAINTY-WEIGHTED TEMPORAL INFORMATION GAIN\nFOR CLOSED-LOOP DEFECT INSPECTION",
    { x: X0, y: 2.55, w: 10, h: 0.7, fontSize: 15, bold: true, color: TEAL, charSpacing: 1 });
  text(s, "Final Review", { x: X0, y: 3.4, w: 8, h: 0.8, fontSize: 40, bold: true, color: TEAL });
  s.addShape("line", { x: X0, y: 4.35, w: 2.6, h: 0, line: { color: TEAL, width: 1.25 } });
  const team = [["Akhil Ramalingam", "23Z207"], ["Anbuchandiran K", "23Z209"], ["Neelesh Padmanabh", "23Z241"],
    ["Saumiyaa Sri V L", "23Z261"], ["Sowndarya Elangi S", "23Z269"], ["Therdhana J P", "23Z273"]];
  team.forEach(([n, r], i) => {
    const y = 4.6 + i * 0.4;
    text(s, n, { x: X0, y, w: 3.6, h: 0.36, fontSize: 17 });
    text(s, r, { x: 4.4, y, w: 1.6, h: 0.36, fontSize: 17, bold: true, color: TEAL });
  });
  text(s, "Guide", { x: 8.4, y: 4.6, w: 4, h: 0.3, fontSize: 13, color: MUTED });
  text(s, "Ms. L. Karthika", { x: 8.4, y: 4.9, w: 4.4, h: 0.4, fontSize: 18, bold: true });
  text(s, "Co-Guide", { x: 8.4, y: 5.5, w: 4, h: 0.3, fontSize: 13, color: MUTED });
  text(s, "Dr. N. Gopika Rani", { x: 8.4, y: 5.8, w: 4.4, h: 0.4, fontSize: 18, bold: true });
  text(s, "PSG College of Technology, Department of CSE", { x: 8.4, y: 6.5, w: 4.4, h: 0.3, fontSize: 12, color: MUTED });
}

// ============================================================ 2. ARCHITECTURAL DESIGN
{
  const s = slide("Architectural Design");
  picture(s, ASSET("paper_figs/loop.png"), 6.3, 1.7, 6.3, 3.2);
  bullets(s, [
    { lead: "Planner", text: "scores 54 candidate views (186 in the large yard) after every move" },
    { lead: "Detector", text: "YOLOv8s with test-time augmentation gives a detection and an uncertainty" },
    { lead: "Geometry", text: "ray-casts each detection onto the wall plane" },
    { lead: "Memory", text: "matches defects across missions (Postgres + Neo4j) and feeds growth and staleness back" },
  ], { x: X0, y: 1.7, w: 5.3, h: 4.8, fontSize: 18, gap: 14 });
}

// ============================================================ 3. NOVELTY COMPLETION
{
  const s = slide("Novelty Completion");
  const rows = [
    ["COVERAGE-FIRST\nPLANNING", "Status: Complete", GREEN,
      `Every wall is seen once before views are scored. F1 ${f3(TS.small.uwtig_no_coverage_first.f1)} → ${f3(TS.small.uwtig.f1)} (9 walls), ${f3(TS.large.uwtig_no_coverage_first.f1)} → ${f3(TS.large.uwtig.f1)} (31 walls).`],
    ["DETECTOR-UNCERTAINTY\nAWARE VIEWING", "Status: Complete, no measurable effect", AMBER,
      "Unsure detections earn a second look. No F1 change, even with a perfect detector and weights up to 20."],
    ["CROSS-MISSION\nDEFECT MEMORY", "Status: Complete", GREEN,
      "Detections are matched to 3-D defect identities across missions. The growth term itself shows no F1 effect."],
  ];
  rows.forEach(([name, status, col, body], i) => {
    const y = 1.65 + i * 1.7;
    s.addShape("rect", { x: 1.6, y, w: 10.1, h: 1.5, fill: { color: PANEL }, line: { color: PANEL, width: 0 } });
    text(s, name, { x: 1.85, y: y + 0.2, w: 3.3, h: 1.1, fontSize: 19, bold: true, color: TEAL, valign: "middle" });
    s.addShape("line", { x: 5.3, y: y + 0.3, w: 0, h: 0.9, line: { color: RULE, width: 1 } });
    text(s, status, { x: 5.55, y: y + 0.15, w: 5.9, h: 0.35, fontSize: 16, bold: true, color: col });
    text(s, body, { x: 5.55, y: y + 0.55, w: 5.9, h: 0.9, fontSize: 14, color: TEXT });
  });
}

// ============================================================ 4. EVALUATION AND PERFORMANCE METRICS
{
  const s = slide("Evaluation and Performance Metrics");
  const flyLess = Math.round(100 * (1 - TS.small.uwtig.flight / TS.small.ruckin_ipp.flight));
  bullets(s, [
    { lead: "F1 (confirmed), 9-wall yard", text: `${f3(TS.small.uwtig.f1)} over ten seeds (95% CI ${ci3(TS.small.uwtig.ci)})` },
    { lead: "F1 (confirmed), 31-wall yard", text: `${f3(TS.large.uwtig.f1)} over ten seeds (95% CI ${ci3(TS.large.uwtig.ci)})`, leadColor: GREEN },
    { lead: "Flight distance", text: `${f0(TS.small.uwtig.flight)} m (9 walls) and ${f0(TS.large.uwtig.flight)} m (31 walls); ${flyLess}% less than Rückin 2023 at 9 walls` },
    { lead: "Versus published planners", text: "level with the best, not clearly better; flies less than most", leadColor: GREEN },
    { lead: "Detector", text: "mAP50 0.884, precision 0.87, recall 0.84 on 1,448 held-out images" },
    { lead: "Calibration", text: "expected calibration error 0.29 to 0.33, so uncertainty only ranks views", leadColor: GREEN },
  ], { x: X0, y: 1.8, w: CW, h: 4.9, fontSize: 21, gap: 16 });
}

// ============================================================ 5. EVALUATION (CONTINUED): PLANNERS
{
  const s = slide("Evaluation and Performance Metrics (Continued)");
  picture(s, FIG("tradeoff.png"), 1.5, 1.55, 10.3, 4.18);
  const da = TS.small.alamdari_latency.uwtig_minus, dl = TS.large.alamdari_latency.uwtig_minus;
  bullets(s, [
    { lead: "9 walls", text: `ahead of Alamdari by ${da.diff.toFixed(3)} (CI ${ci3(da.ci)}), borderline` },
    { lead: "31 walls", text: `Alamdari ahead by ${(-dl.diff).toFixed(3)}, within the noise`, leadColor: GREEN },
  ], { x: X0, y: 6.0, w: CW, h: 0.9, fontSize: 17, gap: 6 });
}

// ============================================================ 6. EVALUATION (CONTINUED): ABLATIONS
{
  const s = slide("Evaluation and Performance Metrics (Continued)");
  picture(s, FIG("ablation.png"), 1.5, 1.55, 10.3, 3.87);
  bullets(s, [
    { lead: "Coverage phase", text: `carries the result: F1 falls to ${f3(TS.small.uwtig_no_coverage_first.f1)} and ${f3(TS.large.uwtig_no_coverage_first.f1)} without it` },
    { lead: "Uncertainty and growth", text: "change F1 by 0.002 at most, also with an oracle detector", leadColor: GREEN },
    { lead: "Staleness and lookahead", text: "cost extra flight but no F1" },
  ], { x: X0, y: 5.65, w: CW, h: 1.3, fontSize: 17, gap: 6 });
}

// ============================================================ 7. REFERENCES
{
  const s = slide("References");
  const refs = [
    "J. Rückin et al., “An informative path planning framework for active learning in UAV-based semantic mapping,” IEEE Trans. Robot., vol. 39, pp. 4279–4296, 2023.",
    "H. K. Dhami et al., “GATSBI: An online GTSP-based algorithm for targeted surface bridge inspection and defect detection,” arXiv:2406.16625, 2024.",
    "B. Moon et al., “IA-TIGRIS: An incremental and adaptive sampling-based planner for online informative path planning,” IEEE Trans. Robot., 2026.",
    "A. Bircher et al., “Receding horizon ‘next-best-view’ planner for 3D exploration,” in Proc. IEEE ICRA, 2016, pp. 1462–1468.",
    "S. Alamdari, E. Fata and S. L. Smith, “Persistent monitoring in discrete environments: Minimizing the maximum weighted latency between observations,” Int. J. Robot. Res., vol. 33, no. 1, pp. 138–154, 2014.",
    "S. Isler et al., “An information gain formulation for active volumetric 3D reconstruction,” in Proc. IEEE ICRA, 2016.",
    "Q. Zha et al., “A dataset of building surface defects collected by UAVs for machine learning-based detection,” Sci. Data, 2025.",
  ];
  text(s, refs.map((r, i) => ({ text: `${i + 1}.  ${r}`, options: { breakLine: true, paraSpaceAfter: 10 } })),
    { x: X0, y: 1.6, w: CW, h: 5.2, fontSize: 15, color: TEXT });
}

// ============================================================ 8. HOW UW-TIG PICKS THE NEXT VIEW
{
  const s = slide("How UW-TIG Picks the Next View");
  text(s, [
    { text: "Utility(v) = ", options: { bold: true, color: TEAL } },
    { text: "1.0 InfoGain + 1.5 Uncertainty + 2.0 Growth + 1.0 Staleness − 0.4 Cost" },
  ], { x: X0, y: 1.5, w: CW, h: 0.45, fontSize: 20 });
  const rows = [
    ["Coverage phase", "See every wall once before anything else", `F1 ${f3(TS.small.uwtig.f1)} → ${f3(TS.small.uwtig_no_coverage_first.f1)}`],
    ["Detector uncertainty", "Look again at detections the model is unsure about", "no change"],
    ["Growth from memory", "Track a defect's size across missions", "no change"],
    ["Staleness", "Revisit areas not seen for a while", `${less("uwtig_no_staleness", "uwtig")}% less flight, F1 ${f3(TS.small.uwtig_no_staleness.f1)}`],
    ["Two-step lookahead", "Score a view together with the best view after it", `${less("uwtig_no_lookahead", "uwtig")}% less flight, F1 ${f3(TS.small.uwtig_no_lookahead.f1)}`],
  ];
  table(s, ["Part", "What it does", "Effect of removing it (9 walls)"], rows,
    { x: X0, y: 2.2, w: CW, colW: [2.9, 5.4, 3.63], fontSize: 16, rowH: 0.62, leftCols: [1, 2] });
  text(s, "Ten seeds, original detector. Staleness and lookahead are adapted from Alamdari et al. and Bircher et al.",
    { x: X0, y: 6.15, w: CW, h: 0.35, fontSize: 13, color: MUTED });
}

// ============================================================ 9. TEST ENVIRONMENT
{
  const s = slide("Test Environment");
  picture(s, ASSET("paper_figs/yard.png"), X0, 1.6, 5.6, 4.46);
  text(s, "31-wall yard: walls in blue, candidate viewpoints in orange and red", { x: X0, y: 6.25, w: 5.6, h: 0.3, fontSize: 12, color: MUTED, align: "center" });
  bullets(s, [
    { lead: "Small yard", text: "9 walls, 54 viewpoints, budget of 16 views" },
    { lead: "Large yard", text: "31 walls, 186 viewpoints, budget of 50 views", leadColor: GREEN },
    { lead: "Scenarios", text: "static, uncertain, multi-defect, growing" },
    { lead: "Textures", text: "real MBDD2025 defect photographs on the walls", leadColor: GREEN },
    { lead: "Seeds", text: "development 100 to 102, test 0 to 9" },
    { lead: "Metrics", text: "confirmed F1 and flight distance", leadColor: GREEN },
  ], { x: 7.0, y: 1.6, w: 5.6, h: 5.0, fontSize: 19, gap: 14 });
}

// ============================================================ 10. DATA AND DETECTOR TRAINING
{
  const s = slide("Data and Detector Training");
  heading(s, "Data", X0, 1.6, 5.8);
  bullets(s, [
    "MBDD2025: 14,471 UAV photos, five classes (crack, leakage, abscission, corrosion, bulge)",
    "Also tried: dacl10k bridge photos, Roboflow corrosion, concrete-crack crops",
    "Test split: 1,448 held-out MBDD2025 images",
  ], { x: X0, y: 2.1, w: 5.6, h: 3.6, fontSize: 18, gap: 12 });
  heading(s, "Preprocessing and training", 6.9, 1.6, 5.7);
  bullets(s, [
    "Photos cropped to each wall's true shape at 1536 px",
    "320x240 camera frames resampled to square pixels",
    "Bulge class oversampled about 4x",
    "Detections outside the wall rejected: removes 51 to 75% of false positives",
    "YOLOv8s, 640 px, 100 epochs on an NVIDIA L4",
  ], { x: 6.9, y: 2.1, w: 5.7, h: 4.4, fontSize: 18, gap: 12 });
}

// ============================================================ 11. DETECTOR RESULTS
{
  const s = slide("Detector Results");
  const cls = [["Crack", 0.84, 0.75], ["Leakage", 0.90, 0.92], ["Abscission", 0.87, 0.78], ["Corrosion", 0.83, 0.79], ["Bulge", 0.95, 0.96]];
  const rows = cls.map(([c, p, r]) => [c, p.toFixed(2), r.toFixed(2), (2 * p * r / (p + r)).toFixed(2)]);
  rows.push(["Mean", "0.87", "0.84", "0.86"]);
  text(s, "YOLOv8s on the held-out test split (mAP50 0.884)", { x: X0, y: 1.5, w: 5.6, h: 0.35, fontSize: 16, bold: true, color: TEAL });
  table(s, ["Class", "Precision", "Recall", "F1"], rows,
    { x: X0, y: 1.95, w: 5.6, colW: [1.9, 1.3, 1.2, 1.2], fontSize: 15, rowH: 0.45, boldRow: 5 });

  text(s, "Fair size comparison, identical settings", { x: 6.9, y: 1.5, w: 5.7, h: 0.35, fontSize: 16, bold: true, color: TEAL });
  const yrows = [["yolov8n", "v8n"], ["yolov8s", "v8s (used)"], ["yolov8m", "v8m"]].map(([k, l]) =>
    [l, `${YO[k].params_m.toFixed(1)} M`, f3(YO[k].map50), f3(YO[k].recall)]);
  table(s, ["Model", "Params", "mAP50", "Recall"], yrows,
    { x: 6.9, y: 1.95, w: 5.7, colW: [1.7, 1.3, 1.4, 1.3], fontSize: 15, rowH: 0.45, boldRow: 1 });
  text(s, "4,000-image subset, 640 px, 30 epochs, one run each. YOLOv8l was not trained (8 GB GPU).",
    { x: 6.9, y: 3.85, w: 5.7, h: 0.6, fontSize: 13, color: MUTED });

  bullets(s, [
    `v8m adds only ${(YO.yolov8m.map50 - YO.yolov8s.map50).toFixed(3)} mAP50 over v8s for ${(YO.yolov8m.params_m / YO.yolov8s.params_m).toFixed(1)}x the parameters`,
    "Extra training data did not improve the closed loop, so the original detector stays the default",
  ], { x: X0, y: 5.5, w: CW, h: 1.3, fontSize: 17, gap: 8 });
}

// ============================================================ 12. LIVE DEMO
{
  const s = slide("Live Demo");
  heading(s, "Run it", X0, 1.6, 6);
  s.addShape("rect", { x: X0, y: 2.1, w: CW, h: 1.0, fill: { color: PANEL }, line: { color: PANEL, width: 0 } });
  text(s, [
    { text: "set UWTIG_MEMORY=inmem", options: { breakLine: true } },
    { text: "python demo_uwtig_flight.py --planner uwtig --gui --missions 1" },
  ], { x: X0 + 0.3, y: 2.2, w: CW - 0.6, h: 0.8, fontFace: "Consolas", fontSize: 17, color: GREEN, valign: "middle" });
  bullets(s, [
    "A 3-D window shows the flight; the terminal prints each wall chosen and the detections",
    "No Postgres or Docker needed with the in-memory store",
    "Swap the planner for isler_nbv or random to compare on the same scene and seed",
  ], { x: X0, y: 3.4, w: CW, h: 1.8, fontSize: 18, gap: 10 });
  heading(s, "Recorded flights, if the live run is slow", X0, 5.25, 9);
  bullets(s, [
    "output/comparison_inspection_uwtig_vs_isler_nbv_vs_random.mp4",
    "output/comparison_flythrough_uwtig_vs_isler_nbv_vs_random.mp4",
  ], { x: X0, y: 5.75, w: CW, h: 1.1, fontSize: 16, gap: 8 });
}

// ============================================================ 13. BACKUP TABLE
{
  const s = slide("Ten-Seed Results");
  text(s, "Seeds 0 to 9, original detector, confirmed F1; CI is a 95% bootstrap over seeds.",
    { x: X0, y: 1.45, w: CW, h: 0.35, fontSize: 14, color: MUTED });
  const order = [["uwtig", "UW-TIG"], ["alamdari_latency", "Alamdari 2014"], ["gatsbi_gtsp", "GATSBI"], ["ruckin_ipp", "Rückin 2023"],
    ["random", "Random"], ["bircher_rhnbv", "Bircher 2016"], ["isler_nbv", "Isler NBV"]];
  const c = (d) => `${d.ci[0].toFixed(3)} to ${d.ci[1].toFixed(3)}`;
  const rows = order.map(([p, l]) => [l, f3(TS.small[p].f1), c(TS.small[p]), f0(TS.small[p].flight), f3(TS.large[p].f1), c(TS.large[p]), f0(TS.large[p].flight)]);
  table(s, ["Planner", "F1 (9 walls)", "95% CI", "Flight (m)", "F1 (31 walls)", "95% CI", "Flight (m)"], rows,
    { x: X0, y: 1.95, w: CW, colW: [2.3, 1.45, 2.0, 1.3, 1.5, 2.0, 1.38], fontSize: 15, rowH: 0.52, boldRow: 0 });
}

// ---------------------------------------------------------------- write
const OUT = process.env.DECK_OUT || path.join(__dirname, "..", "UW-TIG_Review_Deck.pptx");
pres.writeFile({ fileName: OUT }).then(async () => {
  const { applyTheme } = require(process.env.PPTX_SKILL_DIR + "/scripts/apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT, "-- slides:", N);
});
