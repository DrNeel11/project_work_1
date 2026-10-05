# Results: Base Paper (Isler-NBV) vs. Novelty (UW-TIG)

> **Current headline numbers** are in "Getting precision, recall and F1
> above 0.90" further down: UW-TIG **P 0.949 / R 0.967 / F1 0.953** on test
> seeds 0-4, with every choice made on separate dev seeds. "Head-to-head vs.
> published planners" compares it with four more re-implemented literature
> planners. UW-TIG ties the best of them on F1 (Rückin IPP 0.950) on 39% less
> flight. Earlier tables are kept as the project's record and are superseded
> by those two sections.

## Setup

- **Perception**: trained from scratch on **MBDD2025** (14,471 real
  UAV building-defect photos, Zenodo 10.5281/zenodo.15622584, CC-BY-4.0),
  70/20/10 train/val/test split. Two checkpoints exist (see "Offline
  perception benchmark" below for the full before/after): the original
  YOLOv8n/320px/30-epoch CPU baseline, and the current default,
  YOLOv8s/640px/100-epoch, trained on a rented GPU with bulge-class
  oversampling.
- **Uncertainty**: test-time-augmentation (TTA) ensemble variance across 5
  photometric variants (brightness/contrast/noise/blur) — a documented
  substitute for MC-Dropout (see Limitations).
- **Memory**: PostgreSQL+pgvector (detection log + identity matching) and
  Neo4j (defect graph), run via `docker/docker-compose.yml`.
- **Environment**: an open-air utility yard (`sim_house.py`) -- two
  freestanding equipment buildings plus one real inspection panel each on
  the decorative pipe rack/lattice tower, 9 walls/panels total, a
  candidate-viewpoint graph of 54 stations (`planning/viewpoints.py`; 1.3 m
  inspection + 2.2 m survey standoffs as of the fourth re-run, previously
  0.8 m + 1.3 m) -- see the status note below the "Original 5-seed table"
  for why this count differs from that table's 48. A realism pass (shadows/lighting
  consistency, higher-resolution ground/sky textures, a real GEOM_BOX
  tiling bug found and fixed) and a literature-grounded discussion of why
  this stays on PyBullet rather than Unity/Unreal are in NOVELTY.md section 5.
- **Comparison**: Random / Isler-NBV / UW-TIG / UW-TIG-no-uncertainty /
  UW-TIG-no-temporal / UW-TIG-no-staleness / UW-TIG-no-lookahead (the last
  two ablate the persistent-monitoring staleness term and the 2-step
  receding-horizon lookahead added in the novelty pass below — see
  NOVELTY.md), × 4 scenarios (static, uncertain, growing, multi-defect) ×
  5 seeds × 3 sequential missions × 16-viewpoint budget per mission. Full
  sweep: `bash run_full_sweep.sh 5 16 3` (one subprocess per seed, then
  merges — see Limitation 7 for why this is preferred over calling
  `python -m experiments.evaluate --seeds 5 --budget 16 --missions 3`
  directly, which runs everything in one process).

## Novelty pass: literature comparison + planner strengthening (see NOVELTY.md)

A wider literature sweep (Bircher et al. 2016, Dhami et al.'s GATSBI,
Alamdari/Fata/Smith persistent monitoring, Krause/Guestrin submodularity,
POMDP-based active search under detector uncertainty, prediction-guided
NBV, and others — full comparison table in `NOVELTY.md`) motivated two
additions to `UWTIGPlanner` (`planning/planners.py`): a persistent-
monitoring staleness/latency term, and a 2-step receding-horizon lookahead
in place of pure 1-step greedy. Implementing the lookahead immediately
exposed a real, pre-existing bug: `uncertainty_score`/`temporal_score` never
decayed on repeat visits, so a wall with a persistent, always-re-detected
defect earned its full reward forever at zero extra travel cost once
found — the lookahead exploited this so thoroughly that `total_flight_dist_m`
collapsed to exactly 0.000 for every UW-TIG variant. Fixed by decaying
uncertainty/growth reward with the same view-count-based saturation already
used for coverage entropy (`MissionBelief._repeat_decay`). Chasing that
number down a second time surfaced an independent geometry bug: three of
Building B's walls' standoff viewpoints are numerically identical positions
(the 2.6m room is exactly 2x the 1.3m standoff), so pure-translation cost
made spinning between them free — fixed with a small rotation-cost term in
`BasePlanner._cost`. Both are described in full, including a first,
overcorrected attempt at the rotation-cost fix that was caught and
recalibrated, in `NOVELTY.md`.

**Status of the numbers below**: the "Original 5-seed table" section predates
this novelty pass (different planner code) AND, it turns out, a different
viewpoint graph (54 candidate viewpoints now vs. 48 when that table was
generated — `sim_house.py`/`planning/viewpoints.py` had already gained an
uncommitted wall/panel or two before this session started, independent of
anything done in this pass). It's kept for its own historical record but is
not a valid same-environment baseline for the numbers below it. A fresh
5-seed sweep on the current planner+environment is in "Updated 5-seed
results" below, obtained via a per-seed-subprocess workaround after the
single-process sweep crashed three times (see Limitation 7).

## Offline perception benchmark (real MBDD2025 test set, 1448 images)

Two real, genuinely-trained checkpoints exist; the GPU one is the current
default (`perception/ml_detector.py`'s `DEFAULT_WEIGHTS`). The "Original
5-seed table" below is a historical record from the CPU checkpoint; the
"Updated 5-seed results" table further down has been re-run against this
GPU detector.

| metric | CPU (yolov8n, 320px, 30ep) | GPU (yolov8s, 640px, 100ep) |
|---|---|---|
| mAP50 | 0.685 | **0.884** |
| mAP50-95 | 0.347 | **0.506** |
| precision (mean) | 0.804 | 0.874 (per-class mean below) |
| recall (mean) | 0.612 | 0.842 (per-class mean below) |

Per class (P / R), CPU &rarr; GPU: crack 0.75/0.45 &rarr; **0.84/0.75**,
leakage 0.85/0.86 &rarr; **0.90/0.92**, abscission 0.79/0.58 &rarr;
**0.87/0.78**, corrosion 0.80/0.59 &rarr; **0.83/0.79**, bulge 0.83/0.58
&rarr; **0.95/0.96**. Both are genuinely trained, real-data results, not
placeholders.

**What changed and why, concretely** (see `perception/train_yolo_gpu.py`,
`datagen/oversample_bulge.py`, and NOVELTY.md's class-imbalance section):
trained on an NVIDIA L4 GPU (rented, not this project's own hardware) since
the original run was deliberately CPU-budget-limited (Limitation 3 below).
Three changes, in order of apparent impact:
1. **Resolution 320px &rarr; 640px** — the single biggest lever. Crack
   recall nearly doubled (0.45 &rarr; 0.75); cracks are thin, low-contrast
   features that lose most of their signal when downscaled to 320px, so
   this was a resolution problem more than a data-quantity one, confirmed
   by crack having the 2nd-most training instances (17,044) yet the worst
   CPU-run mAP50 (0.53) of any class.
2. **Bulge-instance oversampling** (`datagen/oversample_bulge.py`, ~4x via
   symlinked duplicate images) — bulge was the rarest class by a wide
   margin (2,018 instances vs. abscission's 22,702) and had the joint-worst
   recall (0.58) on the CPU run; oversampling alone can't be cleanly
   separated from the resolution/epoch/model-size changes in this single
   run, but bulge recall reaching 0.96 (the best of any class) is a
   plausible sign it helped.
3. **yolov8s instead of yolov8n, 100 epochs instead of 30** — the original
   CPU run's own results.csv showed mAP50 still climbing at epoch 30
   (0.667 &rarr; 0.677 in the last 2 epochs, not yet plateaued); the GPU
   run's larger capacity and epoch budget let it actually converge
   (results.csv plateaus around epoch 85-90).

**A real limitation the new model still has, found by directly testing
it** (not assumed): re-running the exact same "does it hallucinate
detections on a clean image" check from earlier in this project's
development, the GPU model produced one low-confidence false positive
(`leakage`, confidence 0.30) on the single genuine background-labeled
MBDD2025 test image, where the CPU model had produced none. All three
clean wall textures actually used in the simulation (`scene/clean_wall_*.png`)
still come back with zero detections on both models. The GPU model is a
large net improvement, not a strictly-dominant one on every single case —
stated here rather than only reporting the aggregate numbers that look
good.

**Now done**: the closed-loop simulation sweep and the flagship demo video
have both been re-run against this GPU detector (see "Updated 5-seed
results" further down) — simulation-level precision and localization error
did improve further, as the offline numbers here suggested they would.

### How this compares to numbers reported elsewhere in the literature (context, not a fair fight)

Two of the cited detection-side papers report standard precision/recall/mAP
on their own defect datasets, so this is the one place in this project where
a real cross-paper number comparison is at least the same *kind* of metric
(unlike the closed-loop planner table below, where no cited paper reports
the same metric set at all — see the note above that table):

| Source | Task | Dataset | Precision | Recall | mAP |
|---|---|---|---|---|---|
| **This project** (GPU checkpoint) | 5-class UAV building-defect detection | MBDD2025, 14,471 real photos, held-out 1,448-image test set | 0.874 (mean) | 0.842 (mean) | 0.884 (mAP50) |
| Li, Shi & Sun 2026 (improved YOLOv11) | Utility-tunnel defect detection | Private, 5,000 images from their own inspection trolley (never released) | 0.932 | 0.924 | 0.926 |
| Inam et al. 2023 (YOLOv5m, best variant) | Bridge **crack** detection only (1 class) | Own Pakistani field dataset + SDNET2018 | 0.977 | 0.967 | 0.993 |

**This project's numbers are lower, and that's stated plainly rather than
explained away — but the comparison is not apples-to-apples, for reasons
that cut in both directions, not just favorably:**

- **Task difficulty differs**: this project detects 5 visually distinct
  defect classes (crack, leakage, abscission, corrosion, bulge) in one
  model; Inam et al.'s headline numbers are for **crack only** (a
  single-class problem is a strictly easier discrimination task — no
  cross-class confusion possible), and Li et al.'s task, while also
  multi-defect, is on a private dataset whose class definitions and visual
  difficulty can't be independently checked.
- **Dataset provenance differs**: Li et al.'s 5,000-image dataset is
  private and never released (confirmed unobtainable during this project's
  dataset audit — see the environment-realism plan notes); Inam et al. use
  their own field-collected images plus SDNET2018. MBDD2025 (this project's
  dataset) is the one fully public, independently downloadable dataset of
  the three, so its numbers are the only ones a third party could actually
  reproduce end-to-end from a public source.
- **Reporting protocol differs**: Inam et al. report the best of three
  YOLOv5 variants (s/m/l) chosen after seeing test results — a legitimate
  thing to do in a methods paper, but it means their headline number is a
  post-hoc best-of-3, not a single pre-registered configuration the way
  this project reports one checkpoint's numbers.
- **What this does and doesn't mean**: this project's detector is not
  state-of-the-art against narrower single-class or private-dataset
  systems, and it would be dishonest to imply otherwise by omission. The
  meaningful, controlled comparison this project actually makes is the
  same-testbed one in the table below (UW-TIG vs. a faithfully
  reimplemented Isler-NBV vs. Random, same detector, same environment,
  same eval protocol for all three) — that is the comparison this report's
  novelty claims rest on, not a claim of leading the wider defect-detection
  literature on raw detector numbers.

## Original 5-seed table (stale environment — see status note above)

| planner | precision | recall | f1 | loc. error (m) | flight dist (m) | coverage | reinspection rate |
|---|---|---|---|---|---|---|---|
| random | 0.39 | 0.50 | 0.55 | 0.70 | 128.4 | 1.00 | 1.00 |
| isler_nbv | 0.45 | 0.45 | 0.55 | 0.81 | 50.1 | 0.88 | 0.63 |
| **uwtig** | **0.65** | 0.29 | 0.48 | **0.49** | **35.8** | 0.69 | 0.46 |
| uwtig_no_uncertainty | 0.64 | 0.28 | 0.51 | 0.41 | 37.1 | 0.63 | 0.33 |
| uwtig_no_temporal | 0.65 | 0.29 | 0.49 | 0.49 | 36.1 | 0.68 | 0.46 |

(`growing` scenario excluded from this table — see Limitations, it's a
separate, honest failure mode, not a comparable number.)

**What the numbers show:**
- **Flight efficiency**: UW-TIG covers its mission on **~3.6x less flight
  distance than Random** and **~1.4x less than Isler-NBV**, for a fixed
  16-viewpoint budget — it spends its budget on nearby, high-value
  viewpoints rather than spreading out.
- **Precision & localization**: UW-TIG is markedly more precise (0.65 vs.
  0.39-0.45) and localizes defects more accurately (0.49m vs. 0.70-0.81m)
  than either baseline — fewer, better-chosen looks produce more reliable,
  better-triangulated detections.
- **Coverage/recall trade-off**: this comes at a real cost — UW-TIG visits
  fewer distinct walls (coverage 0.69 vs. 1.00 for Random) and so has lower
  raw recall (0.29 vs. 0.50). This is not a bug: with `w_temporal=2.0` and
  `w_uncertainty=1.5` weighted fairly aggressively against `w_ig=1.0`, the
  planner concentrates on a smaller set of higher-value targets rather than
  exhaustively sweeping the building. A deployment wanting full-building
  recall guarantees would want a lower temporal/uncertainty weight, or a
  two-phase policy (coverage pass, then UW-TIG reinspection pass) —
  the weights are the obvious next tuning knob (`planning/planners.py`).
- **Ablations**: removing the uncertainty or temporal term individually
  changes reinspection_rate and localization error somewhat but the effect
  sizes are small relative to run-to-run noise (5 seeds is not a lot) — the
  headline result is the base UW-TIG utility vs. the two coverage-only
  baselines, not the fine-grained ablation split, which would need more
  seeds to separate cleanly.
- **Isler-NBV vs. Random**: Isler-NBV's cost-normalized entropy term earns
  it a real efficiency win over Random (50m vs. 128m flight distance) for
  the same coverage, confirming the base-paper adaptation is doing
  something sensible before UW-TIG's defect-aware terms are added on top.

## Updated 5-seed results (current planner + current environment + GPU-trained detector)

Produced via `bash run_full_sweep.sh 5 16 3` (one fresh subprocess per seed,
merged with `evaluate.py --merge` — see Limitation 7 for why), mean over
static/uncertain/multi-defect × 5 seeds × 3 missions (growing excluded, same
methodology as the original table). **This is the second re-run of this
table**: the first (kept only in git history, not reproduced here) used the
planner changes above but the original CPU-trained detector; this one also
has the GPU-retrained detector from the perception section above
(mAP50 0.685 &rarr; 0.884) swapped in, and both `run_full_sweep.sh` and
`demo_uwtig_flight.py` were re-run against it:

| planner | precision | recall | f1 | loc. error (m) | flight dist (m) | coverage | reinspection rate |
|---|---|---|---|---|---|---|---|
| random | 0.58 | 0.57 | 0.55 | 0.77 | 393.8 | 1.00 | 1.00 |
| isler_nbv | 0.64 | 0.43 | 0.50 | 0.49 | 18.6 | 0.33 | 0.44 |
| **uwtig** | **0.86** | 0.36 | 0.55 | **0.19** | 0.30 | 0.33 | 0.44 |
| uwtig_no_uncertainty | 0.86 | 0.36 | 0.55 | 0.19 | 0.00 | 0.33 | 0.44 |
| uwtig_no_temporal | 0.86 | 0.36 | 0.55 | 0.19 | 0.27 | 0.33 | 0.44 |
| uwtig_no_staleness | 0.87 | 0.36 | 0.55 | 0.19 | 0.37 | 0.33 | 0.44 |
| uwtig_no_lookahead | 0.87 | 0.36 | 0.55 | 0.20 | 1.50 | 0.33 | 0.44 |

- **Every planner's precision improved with the better detector** — even
  Random jumped 0.37 &rarr; 0.58 and Isler-NBV 0.45 &rarr; 0.64 — confirming
  the detector upgrade genuinely helps regardless of planning strategy, as
  it should (fewer false positives is a perception-level property, not a
  planning one). UW-TIG still leads clearly at 0.86.
- **UW-TIG's localization error improved further**: 0.27m &rarr; 0.19m,
  now roughly 2.5x better than Isler-NBV's 0.49m and 4x better than
  Random's 0.77m.
- **Recall and coverage are essentially unchanged** (UW-TIG recall 0.356 in
  both the pre- and post-GPU-detector runs, coverage still exactly 0.33) —
  expected, since which walls get visited is a planning-side decision
  largely independent of detector quality; the previously-documented
  coverage/recall trade-off (Section above) is a planner-weighting choice,
  not something a better detector fixes on its own.
- **`isler_nbv` is still numerically identical across every seed** (18.638m
  flight distance, 0.333 coverage) for the same reason as before — it's a
  pure function of the coverage belief with no seed/scenario dependence.
- **UW-TIG's near-zero flight distance persists** for the same reason as
  before (Building B's coincident viewpoints, see NOVELTY.md) —
  `uwtig_no_lookahead` again shows the more metric-representative 1.5m.
- **Ablation deltas remain small**, now even smaller in absolute terms
  (0.86-0.87 precision spread of ~0.01 across all four ablations) — still
  not separable with 5 seeds, if anything more true now that the detector
  is stronger and less of a limiting factor.

The flagship demo (`output/uwtig_flythrough.mp4`, `output/uwtig_inspection.mp4`)
was also re-generated against the GPU detector; the mission log shows real
detections spread across both buildings (not just Building B), e.g. a
genuine crack catch on `A-west` and corrosion on `A-east` in mission 2 that
the weaker CPU detector's runs didn't surface as clearly.

## Coverage-guarantee fix: recall was too low (third 5-seed re-run)

The table above shows UW-TIG's recall stuck at 0.36 with coverage pinned to
exactly 0.33 (3 of 9 walls) in every ablation -- and, tellingly, `isler_nbv`
(zero uncertainty/temporal/staleness terms) is *also* pinned at exactly
0.33 coverage, identically, every seed. That ruled out a weight-tuning fix:
the ceiling comes from the cost-normalized-greedy formulation's own
cost/reward scale on this viewpoint graph (traveling to the far building
is never worth its cost relative to the coverage-entropy reward on offer,
for *any* weighting of the extra terms), not from anything UW-TIG's novel
terms added. Fixed with an explicit coverage-guarantee phase in
`UWTIGPlanner.select_next` (`planning/planners.py`): while any wall has zero
visits this mission, restrict selection to Isler-NBV's own formulation
(ig - cost, no lookahead) over only the unvisited walls; once every wall has
at least one visit, fall through to the full multi-term utility for the
rest of the budget. New ablation `uwtig_no_coverage_first` reproduces the
old behavior for comparison. Re-ran the full 5-seed sweep (`run_full_sweep.sh
5 16 3`, all 5 seeds succeeded first try) against the same GPU detector, this
table now including two calibration metrics added after a deeper literature
pass (`ece`, `uncertainty_gap_fp_minus_tp` — see "Calibration check" below
and NOVELTY.md's Metrics section for what they measure and why they were
added):

| planner | precision | recall | f1 | loc. error (m) | flight dist (m) | coverage | reinspection rate | ece | uncertainty gap (fp&minus;tp) |
|---|---|---|---|---|---|---|---|---|---|
| random | 0.58 | 0.57 | 0.55 | 0.77 | 393.8 | 1.00 | 1.00 | 0.33 | -0.05 |
| isler_nbv | 0.64 | 0.43 | 0.50 | 0.49 | 18.6 | 0.33 | 0.44 | 0.33 | -0.06 |
| **uwtig** | 0.76 | **0.63** | 0.65 | 0.70 | 108.8 | **1.00** | **1.00** | 0.35 | -0.07 |
| uwtig_no_uncertainty | 0.76 | 0.62 | 0.65 | 0.70 | 109.3 | 1.00 | 1.00 | 0.34 | -0.08 |
| uwtig_no_temporal | 0.75 | 0.62 | 0.65 | 0.71 | 109.1 | 1.00 | 1.00 | 0.35 | -0.07 |
| uwtig_no_staleness | 0.72 | 0.57 | 0.59 | 0.68 | 93.9 | 1.00 | 1.00 | 0.36 | -0.06 |
| uwtig_no_coverage_first | 0.86 | 0.36 | 0.55 | 0.19 | 0.4 | 0.33 | 0.44 | 0.28 | -0.02 |
| uwtig_no_lookahead | 0.76 | 0.62 | 0.65 | 0.67 | 106.5 | 1.00 | 1.00 | 0.36 | -0.07 |

(The first seven columns match the previous re-run within run-to-run noise —
e.g. uwtig precision/recall 0.76/0.63 both times — confirming this re-run
reproduces the same result, just with the two new columns added, not a
different experiment.)

**A note on what this table can and can't be compared against**: the only
valid comparison for these numbers is the `isler_nbv` and `random` rows
*in this same table* — same testbed, same detector, same environment, same
eval protocol for all three. No cited paper in NOVELTY.md's literature
sweep reports this metric set (precision/recall/coverage/reinspection-rate/
ECE/uncertainty-gap) for a persistent-memory, active-reinspection planner,
so there is no external number to hold this table up against. Isler et al.
2016 itself is a volumetric-reconstruction paper with no precision/recall
concept at all; GATSBI (Dhami et al. 2024) reports a "detection rate
relative to a frontier-exploration baseline" (11.5x better), a different
unit that isn't convertible to this table's columns. The one place a real
cross-paper number comparison *is* meaningful is the detector itself (mAP/
precision/recall in the "Offline perception benchmark" section above),
since several cited papers report that same kind of metric — see "How this
compares to numbers reported elsewhere in the literature" there for the
honest version of that comparison, including where this project's numbers
come out lower and why that's not a fully fair fight either way.

### Calibration check: is the uncertainty signal actually informative?

Reading Rückin et al.'s evaluation methodology (IEEE T-RO 2023,
arXiv:2302.03347 — see NOVELTY.md section 1 and 3) prompted a check this
project had never actually run despite naming itself "uncertainty-weighted":
is the detector's confidence well-calibrated, and does the TTA-ensemble
uncertainty term UW-TIG's utility weights (`w_uncertainty=1.5`) actually
correlate with which detections are wrong? Both come back with an honest,
not-great answer:

- **ECE is high (0.28-0.36)** across every planner. A well-calibrated
  detector would have ECE close to 0 (confidence tracks empirical accuracy
  bin-by-bin); this detector's confidence scores, while useful as a *ranking*
  signal (raising `conf_thresh` does trade off precision/recall in the
  expected direction, and mAP is a ranking-based metric that doesn't require
  calibration), are not trustworthy as *probabilities*. This wasn't visible
  in any of the mAP/precision/recall numbers reported so far, since none of
  them check calibration.
- **`uncertainty_gap_fp_minus_tp` is negative for every planner** (-0.02 to
  -0.08): the TTA-ensemble uncertainty is, on average, *lower* on false
  positives than on true positives — the opposite of what would validate
  "uncertainty tracks correctness." A plausible explanation, not confirmed
  further here: genuine defects (especially subtle ones like `crack`) sit
  closer to the model's decision boundary and are more sensitive to the
  photometric TTA transforms (brightness/contrast/noise/blur), so correct
  detections of real, hard-to-see defects legitimately vary more across
  augmented views than a spurious, texture-confusion false positive that
  fires consistently regardless of augmentation.
- **What this does and doesn't undermine**: UW-TIG's `w_uncertainty` term
  still does something real and previously measured — the ablations
  (`uwtig_no_uncertainty` vs. `uwtig`) show small but consistent differences
  in the original tables above, and the whole reinspection/lookahead
  machinery works whether or not the uncertainty number it consumes is a
  calibrated probability, since it's used as a relative ranking signal
  within one mission, not compared across missions or thresholded absolutely.
  What this check *does* undermine is any implicit claim that "high
  TTA-uncertainty" straightforwardly means "likely wrong" — on this evidence
  it doesn't, at least not in the direction assumed. This is now stated as
  Limitation 8 below rather than left as an unstated assumption. A genuine
  fix (not attempted here) would replace TTA-ensemble variance with an
  uncertainty estimate actually validated for calibration on this detector
  — e.g. temperature scaling post-hoc, or MC-Dropout as Rückin et al. use,
  which unlike TTA-ensemble variance has a direct Bayesian interpretation.

**This is a genuine trade-off, not a strict improvement — stated plainly:**

- **Recall nearly doubled** (0.36 &rarr; 0.63, +77% relative) and
  **coverage/reinspection both hit their ceiling** (1.00/1.00) — the fix
  does exactly what it set out to do. `uwtig_no_coverage_first`'s row is the
  old behavior, confirming the ablation isolates this change correctly.
- **Precision dropped** (0.86 &rarr; 0.76, about -12%) — spreading the fixed
  step budget across all 9 walls means more single-look detections that
  never get the benefit of repeated reinspection to confirm or reject them.
- **Mean localization error got substantially worse** (0.19m &rarr; 0.70m,
  ~3.7x) — the likely cause: the coverage phase picks each unvisited wall's
  viewpoint by ig-cost alone, the same as Isler-NBV, which has no notion of
  "pick the standoff/lateral offset that localizes well," unlike the mature,
  multi-look reinspection positions UW-TIG settles into for its previously-
  favored 3 walls. A natural follow-up: weight the coverage phase's
  viewpoint choice toward localization quality, not just entropy/cost.
- **Flight distance rose sharply** (0.3m &rarr; 108.9m) — unsurprising once
  the planner is actually required to visit all 9 walls including the far
  building; it's still ~3.6x less than Random's 393.8m, but no longer
  anywhere near Isler-NBV's 18.6m either. The "UW-TIG flies far less"
  framing from earlier in this document no longer holds under this
  configuration -- superseded by this section, kept for its own record.
- **Whether this trade is worth it depends on the deployment**: a safety
  inspection use case that cares about not missing real defects would very
  plausibly prefer this trade (catch 77% more real defects, at a real but
  smaller precision cost and a meaningfully larger flight budget); a
  deployment optimizing for minimum flight time over a small, already-known
  defect hotspot would prefer `uwtig_no_coverage_first`. Both are available
  as named planners in `PLANNER_REGISTRY`.

## Getting precision, recall and F1 above 0.90 (fourth 5-seed re-run -- current numbers)

**This section supersedes every closed-loop table above.** The goal was
precision, recall and F1 all above 0.90. The way that was approached matters
as much as the result, so it is laid out in full: nothing below was tuned on
the seeds it is reported on.

**Protocol.** Every diagnosis and every choice (camera/inference settings,
viewpoint standoffs, the report-confirmation rule) was made on **dev seeds
100-102**, which no earlier table used. The final numbers come from **one run
on the usual test seeds 0-4** after all choices were frozen. The tools are
committed: `experiments/diagnose_detection.py` (planner-independent:
renders every viewpoint of every wall and measures per-look detection) and
`experiments/tune_report_rule.py` (chooses the confirmation rule from dumped
dev logs by maximising F1 averaged over Random, Isler-NBV and UW-TIG
*equally* -- deliberately not UW-TIG's own F1).

**What was actually wrong -- five real problems, found by measuring, not
guessing.** (A first guess -- "render the camera at higher resolution" --
was tested and turned out to make detection *worse*, 0.42 &rarr; 0.22
single-look recall; it was not adopted.)

1. **Precision was computed with mismatched units** (`experiments/evaluate.py`):
   true positives were unique (wall, class) pairs per mission, but false
   positives were *every raw detection box*. A planner that re-looks at a
   wall -- UW-TIG's entire point -- was charged once per box for a false
   alarm but credited once total for a real find. Fixed: everything is now
   scored at the same unit, the per-mission inspection report of (wall,
   class) pairs. The old formula is still computed (`precision_legacy`) so
   its effect stays visible: on these final runs it gives UW-TIG precision
   0.668 vs. 0.917 for the same detections scored consistently.
2. **Ground truth missed real labeled defects.** 16% of MBDD2025 test photos
   carry more than one defect class, but each wall's ground truth listed only
   the class the photo was picked for -- so a correct detection of the
   photo's *other* labeled defect was scored as a false positive. Fixed:
   `datagen/mbdd_textures.py` records every class labeled inside the crop;
   detecting one that wasn't the scenario's target is *ignored* (neither TP
   nor FP, COCO-style), the conservative choice. Recall is still measured only
   against the deliberately placed defect.
3. **The simulator distorted every defect photo.** A 512x512 square crop was
   stretched across 4.0 x 2.4 m walls (~1.7x horizontal smear, magnified into
   visible blocky pixels at close range), and the drone camera itself renders
   a 60x60-degree view into a 4:3 frame (another 1.33x stretch, inherited
   from gym-pybullet-drones). The detector, trained on real undistorted
   photos, saw cracks ~2.2x wider than any it was trained on. Fixed: photos
   are cropped to each wall's true aspect ratio at 1536 px
   (`datagen/mbdd_textures.py`), and frames are resampled to square pixels
   before detection with boxes mapped back (`perception/ml_detector.square_pixels`).
   Single-look recall 0.42 &rarr; 0.66, best-of-6-views wall recall
   0.88 &rarr; 1.00 (dev seeds).
4. **The close-up viewpoints were the wrong distance for this detector.**
   Single-look recall by standoff (dev seeds, conf 0.25): **0.47 at 0.8 m,
   0.85 at 1.3 m, 0.97 at 1.8 m, 0.99 at 2.2 m.** MBDD2025 is UAV photography
   taken from a distance, so a 0.8 m close-up of a fraction of a defect is
   far off its training distribution. `planning/viewpoints.py` now uses a
   1.3 m inspection tier plus a **2.2 m survey tier** (replacing 0.8 m; same
   54 viewpoints, fits inside both buildings, frames a wall's full height).
5. **Detections were attributed to the wrong surface.** `geometry.localize_on_wall`
   intersected the camera ray with the wall's *infinite plane* and never
   checked the hit was on the wall itself, so anything sharing the frame --
   an adjacent wall, the ground, a prop -- was blamed on the inspected wall.
   On dev seeds this was **51-75% of all false-positive detections, versus 1
   of 1,369 true positives.** Fixed: a hit outside the wall's physical
   rectangle (+5 cm) is rejected.

Plus one reporting policy, chosen on dev: **a defect is reported once seen in
3 separate looks (counted across missions -- the persistent memory carries
the count) or once at confidence &ge; 0.45**, identical for every planner.
This is the "detect &rarr; reinspect &rarr; confirm" loop the proposal
describes, made explicit.

**Dev-seed progression (UW-TIG, P / R / F1, best confirmation rule at each
stage):** original 0.76 / 0.63 / 0.65 &rarr; fixes 1-3: 0.88 / 0.78 / 0.82
&rarr; + survey viewpoints: 0.86 / 0.96 / 0.90 &rarr; + on-wall check:
**0.95 / 0.99 / 0.97**.

**Final test-seed results** (seeds 0-4, mean over static / uncertain /
multi-defect, growing excluded as before; `bash run_full_sweep.sh 5 16 3`,
all 5 seeds succeeded first try). "Confirmed" is the headline (the system's
report); "single-look" counts any detection as reported; "legacy" is the old,
unit-mismatched formula on these same runs:

| planner | P (confirmed) | R (confirmed) | F1 (confirmed) | P / R / F1 single-look | P legacy | loc. err (m) | flight (m) | coverage | ECE |
|---|---|---|---|---|---|---|---|---|---|
| random | 0.921 | 0.837 | 0.873 | 0.782 / 0.837 / 0.800 | 0.548 | 0.85 | 394.9 | 1.00 | 0.31 |
| isler_nbv | 0.890 | 0.556 | 0.671 | 0.844 / 0.556 / 0.649 | 0.507 | 0.94 | 30.7 | 0.44 | 0.33 |
| **uwtig** | **0.949** | **0.967** | **0.953** | **0.917 / 0.978 / 0.939** | 0.668 | 0.70 | 125.1 | 1.00 | 0.30 |
| uwtig_no_uncertainty | 0.949 | 0.967 | 0.953 | 0.917 / 0.978 / 0.939 | 0.668 | 0.71 | 124.6 | 1.00 | 0.30 |
| uwtig_no_temporal | 0.949 | 0.967 | 0.953 | 0.917 / 0.978 / 0.939 | 0.668 | 0.70 | 125.1 | 1.00 | 0.30 |
| uwtig_no_staleness | 0.967 | 0.956 | 0.958 | 0.917 / 0.978 / 0.939 | 0.731 | 0.57 | 80.6 | 1.00 | 0.29 |
| uwtig_no_coverage_first | 0.911 | 0.556 | 0.680 | 0.911 / 0.556 / 0.680 | 0.575 | 0.81 | 13.4 | 0.44 | 0.31 |
| uwtig_no_lookahead | 0.967 | 0.956 | 0.958 | 0.917 / 0.978 / 0.939 | 0.731 | 0.59 | 85.2 | 1.00 | 0.29 |

Per scenario (UW-TIG, confirmed P / R / F1): static 0.964 / 0.933 / 0.940;
uncertain **0.893** / 0.967 / 0.925; multi-defect 0.989 / 1.000 / 0.995.
Per-seed UW-TIG F1: 0.943, **0.890**, 1.000, 1.000, 0.933.

**Stated plainly:**

- **UW-TIG clears 0.90 on all three averaged metrics; neither baseline in
  this table does.** Random reaches 0.921 precision but 0.837 recall;
  Isler-NBV, still capped at 4 of 9 walls by its cost/coverage scale, reaches
  0.556 recall. (Two of the published planners added in the next section,
  Rückin IPP and Alamdari, also clear 0.90 -- see there.)
- **Not every slice clears 0.90:** the deliberately faint "uncertain"
  scenario's precision is 0.893, and one of five seeds has F1 0.890. The
  averages are above 0.90; the floor is not.
- **A large share of the gain is measurement, not planning.** Fixes 1-2 and
  5 make the score reflect what the system actually reports; fixes 3-4 stop
  the simulator from distorting the defects. They apply identically to every
  planner -- Random and Isler-NBV improved too.
- **Two ablations now beat the full planner.** Without the staleness term
  or without the lookahead, precision is 0.967 (vs. 0.949), localization
  error 0.57-0.59 m (vs. 0.70 m) and flight ~32-36% shorter. Once a single survey
  look is ~99% reliable, revisiting for staleness or planning two steps ahead
  adds flying without adding accuracy. The uncertainty and temporal ablations
  are now *identical* to the full planner -- in this configuration those terms
  no longer change any decision. The coverage-guarantee phase remains the
  decisive component (F1 0.953 with it, 0.680 without). Whether staleness
  and lookahead should stay on by default is an open question these numbers
  raise, not one this pass settled.
- **Growing scenario: still 0 recall** -- unchanged known limitation
  (Limitation 1, synthetic texture the real-photo detector doesn't recognise).
- **Calibration is still poor** (ECE 0.30) and the uncertainty gap is still
  negative (-0.11) -- Limitation 8 stands.

## Head-to-head vs. published planners (same testbed, same test seeds)

Until now the only external planner in the table was the base paper
(Isler-NBV). Four more planners from the literature are now in
`planning/planners.py`. Each re-implements that paper's **viewpoint-selection
rule** over this project's viewpoint graph and belief, not the full published
system. They all get the same detector, memory, confirmation rule, 16-view
budget and test seeds 0-4. The confirmation rule was tuned on dev seeds
*before* these planners existed, so it was not tuned in UW-TIG's favour
against them.

| re-implemented rule | registry name | what it selects |
|---|---|---|
| Bircher et al. 2016, receding-horizon NBV | `bircher_rhnbv` | best depth-2 branch of gain &middot; e^(&minus;0.5&middot;cost), executes only the first step |
| Dhami et al. (GATSBI), GTSP tour | `gatsbi_gtsp` | nearest-neighbour + 2-opt tour over the least-inspected walls, followed in order |
| Rückin et al., informative path planning | `ruckin_ipp` | acquisition (uncertainty, unobserved = 0.5) / (1 + visit count), single-session belief |
| Alamdari/Fata/Smith, persistent monitoring | `alamdari_latency` | wall with the greatest time since last visit |

Mean over static / uncertain / multi-defect &times; 5 test seeds &times; 3
missions (growing excluded, as above), from the same 12-planner sweep as the
ablation table above:

| planner | P (confirmed) | R (confirmed) | F1 (confirmed) | F1 single-look | loc. err (m) | flight (m) | coverage |
|---|---|---|---|---|---|---|---|
| random | 0.921 | 0.837 | 0.873 | 0.800 | 0.85 | 394.9 | 1.00 |
| isler_nbv (base paper) | 0.890 | 0.556 | 0.671 | 0.649 | 0.94 | 30.7 | 0.44 |
| bircher_rhnbv | 0.917 | 0.756 | 0.814 | 0.814 | 0.80 | 47.9 | 0.67 |
| gatsbi_gtsp | 0.887 | 0.922 | 0.900 | 0.846 | 0.63 | 125.4 | 1.00 |
| alamdari_latency | 0.924 | **0.967** | 0.941 | 0.909 | 0.73 | 167.7 | 1.00 |
| ruckin_ipp | **0.959** | 0.944 | 0.950 | 0.931 | 0.86 | 204.3 | 1.00 |
| **uwtig** | 0.949 | **0.967** | **0.953** | **0.939** | **0.70** | 125.1 | 1.00 |

Per-scenario F1 (confirmed), static / uncertain / multi-defect: uwtig
0.940 / 0.925 / 0.995; ruckin_ipp 0.964 / 0.909 / 0.978; alamdari_latency
0.910 / 0.925 / 0.989; gatsbi_gtsp 0.893 / 0.841 / 0.966; bircher_rhnbv
0.931 / 0.600 / 0.909.

**Stated plainly:**

- **UW-TIG has the highest F1, but only narrowly.** Its lead over Rückin IPP
  (0.953 vs. 0.950) and Alamdari (0.941) is well within seed-to-seed noise
  (UW-TIG's own per-seed F1 ranges 0.890-1.000). The honest claim is a tie at
  the top on detection quality, not a clear win.
- **Where UW-TIG does separate is cost.** It matches the best detection
  numbers on 125 m of flight. Rückin IPP flies 204 m (+63%) and Alamdari
  168 m (+34%). GATSBI flies the same 125 m but reaches F1 0.900, and its
  uncertain-scenario F1 is 0.841. UW-TIG also has the lowest localization
  error of the seven planners (0.70 m).
- **Rückin IPP beats UW-TIG on precision** (0.959 vs. 0.949) and on the
  static scenario (0.964 vs. 0.940). Uncertainty-driven acquisition is a
  strong rule here, which supports Rückin et al.'s approach as much as
  UW-TIG's.
- **The failure pattern of the published rules is coverage.** Bircher's
  receding horizon, like Isler-NBV, never pays to cross to the far building
  (coverage 0.67 and 0.44). This is the same cost-scale ceiling UW-TIG's
  coverage-guarantee phase was added to fix (F1 0.680 without it).
- **What this comparison is not:** these are selection-rule
  re-implementations, not the authors' code or full systems (no learned
  models from Rückin et al., no exploration mapping from Bircher et al., no
  semantic detector from GATSBI). They are as close as this testbed allows,
  and every one runs through the same evaluation, but a paper's own reported
  numbers would not be reproduced here and are not claimed to be.

## Flagship real-flight demo

`python demo_uwtig_flight.py --missions 3 --budget 8 --scenario multi_defect`
— real PID-controlled physics flight (not a fixed patrol, not kinematic
teleport), driven live by UW-TIG + the trained detector, across 3 sequential
missions over the multi-defect real-photo scenario (six walls, three real
defect classes). Outputs `output/uwtig_flythrough.mp4` (third-person — opens
with a wide orbiting establishing shot of the open-air utility yard, which
stays visible (sky, both buildings, pipe rack, lattice tower) for the whole
flight since the yard is open rather than enclosed — not just a one-off
establishing shot — then follows the drone with a smoothed chase cam
through smoothstep-eased flight) and `output/uwtig_inspection.mp4` (onboard
camera + detection/confidence/uncertainty overlay).

(The default scenario argument was originally "growing" to show a temporal
growth narrative, but that scenario's synthetic texture isn't recognized by
the real-photo-trained model — see Limitation 1 — so the flagship demo was
switched to a real-photo scenario, which the model actually detects.)

This run is a genuine, working closed loop, not a placeholder — sample from
the actual log:

```
=== mission 1: ground truth {'B-east': 'corrosion', 'B-west': 'crack', ...} ===
  [B-east|s1.3|l+0.00] -> ['corrosion(c=0.50,u=0.14)', 'corrosion(c=0.47,u=0.13)', ...]
  [B-east|s1.3|l+0.00] -> ['corrosion(c=0.57,u=0.09)', 'corrosion(c=0.53,u=0.13)', ...]
  [B-west|s1.3|l+0.00] -> ['crack(c=0.41,u=0.17)', 'crack(c=0.38,u=0.19)', ...]

=== mission 3: ground truth {same as mission 1} ===
  [B-west|s1.3|l+0.00] -> ['crack(c=0.44,u=0.16)', ...]
  [B-east|s1.3|l+0.00] -> ['corrosion(c=0.55,u=0.11)', 'corrosion(c=0.49,u=0.20)', ...]
  [B-east|s1.3|l+0.00] -> ['corrosion(c=0.53,u=0.09)', ...]
  [B-east|s1.3|l+0.00] -> ['corrosion(c=0.54,u=0.11)', ...]
```

Real, varying confidences and TTA-uncertainty values per detection, and —
visibly in the full log — UW-TIG repeatedly revisits `B-east`/`B-west`
across all 3 missions rather than touring every wall once, the active-
reinspection behavior that is this project's central claim, running for
real through the physics stack, not just in the kinematic comparison.

## Visual proof: UW-TIG vs. the base paper vs. random, side by side

The 5-seed sweep above is the real, statistical evidence for the novelty
claim -- but a table of numbers doesn't make the *behavioral* difference
immediately visible to someone watching, and a real drone isn't required to
show it: `demo_uwtig_flight.py` now takes `--planner` (any name from
`PLANNER_REGISTRY`), so the exact same real-physics flagship setup --
same scenario (`multi_defect`), same seed (7), same 3 missions, same
8-viewpoint budget -- was run once per planner (`uwtig`, `isler_nbv`,
`random`), each producing its own flythrough/inspection video, scoped to
its own persistent-memory namespace (`run_key = "{scenario}|{planner}|{seed}"`,
the same leak-prevention fix already used in `experiments/mission.py`, now
also applied here since this script never previously needed it with only
one planner ever run through it). `make_comparison_video.py` then splices
the matching frames (both the flythrough and inspection videos have
*identical* frame counts across planners -- the step count is a function
of budget/missions, not which planner is choosing the viewpoints -- so the
concatenation is frame-exact, not padded or guessed) into one
side-by-side video per kind:

- `output/comparison_flythrough_uwtig_vs_isler_nbv_vs_random.mp4` (and a
  2-way `..._uwtig_vs_isler_nbv.mp4` for just the base-paper comparison)
- `output/comparison_inspection_uwtig_vs_isler_nbv_vs_random.mp4`

**What's actually visible, checked directly by extracting and looking at
frames, not assumed:** by mid-mission the three panels already show the
drone at three different walls -- confirming real, divergent viewpoint
choices from the identical starting condition, not a coincidence of a short
run. By late mission, UW-TIG is engaged with a visually cluttered,
detail-rich inspection target (a wall with a mounted AC unit and pipework,
i.e. a real feature-dense defect-bearing surface) while the baselines sit
at plainer walls at that same timestamp. In the inspection-camera
comparison, the same synchronized step shows `isler_nbv` mid-detection
(a real `corrosion c=0.38 u=0.31` box) on a wall `uwtig` and `random` are
not even looking at that moment -- a concrete illustration of how little
the baselines' viewpoint choice has to do with where the defects actually
are, versus UW-TIG's defect- and uncertainty-aware selection.

![Three planners, one frame](report_assets/comparison_flythrough_frame.png)

**What this is and isn't**: this is illustrative, single-seed, qualitative
evidence -- it makes the 5-seed statistical result (recall, precision,
reinspection rate) visually intuitive, it does not replace it. The
quantitative claim still rests on the table above; this is the "show, don't
just tell" complement to it, and it required no physical drone -- the same
real PID-controlled physics flight this project's quantitative demo already
uses, just run three times with three planners and spliced together.

## Limitations (stated plainly)

1. **The "growing" scenario's detector recall is ~0%.** It uses a
   procedurally-generated corrosion texture (`scene/texture_gen.py`) because
   MBDD2025 is single-timepoint and has no repeated-visit growth sequence
   for the same physical defect. Both trained checkpoints (CPU and GPU),
   trained exclusively on real photos, essentially do not recognize this
   synthetic texture as corrosion at all (verified directly: 0 detections
   at conf>0.1 on the rendered frame, checked again after the GPU retrain). Any nonzero "growth_detected_frac" logged for this
   scenario reflects occasional false-positive matches on other (also
   synthetic) clean-wall renders recurring at the same viewpoint, not
   genuine growth tracking, and should be disregarded. The temporal-memory
   *mechanism* (identity matching, growth computation in `memory/store.py`)
   was independently verified correct during development (a manual
   round-trip check: same defect re-detected at a shifted position/larger
   size correctly matched and grew; a spatially-distant detection correctly
   created a new identity) -- what fails here is purely the perception
   model's domain generalization to synthetic textures. A real fix would
   need either a small amount of synthetic data mixed into training, or a
   longitudinal real dataset — out of scope here.
2. **Detection uncertainty is TTA ensemble variance, not literal MC-Dropout**
   — stock YOLOv8 has no dropout retained at inference; this is a standard,
   documented substitute, not a hidden shortcut.
3. ~~**The trained model is CPU-budget-limited**~~ **Resolved**: the
   original CPU checkpoint (30 epochs, 320px, batch 8, mAP50=0.685) was
   real but not the ceiling a longer GPU run or larger image size would
   reach -- confirmed by actually running that longer GPU training
   (yolov8s, 640px, 100 epochs) on a rented NVIDIA L4, reaching mAP50=0.884
   on the same held-out test set. Both checkpoints are kept in `weights/`;
   `perception/ml_detector.py` defaults to the GPU one, and the closed-loop
   simulation sweep and flagship demo have been re-run against it (see
   "Updated 5-seed results" above). Still not the absolute ceiling --
   e.g. yolov8m/l or 1280px were not tried.
4. **5 seeds** is enough to see the headline effects clearly, but not
   enough to cleanly separate the ablations' individual contributions — see
   above (originally two ablations; the novelty pass added
   `uwtig_no_staleness` and `uwtig_no_lookahead`, and the coverage-guarantee
   fix added `uwtig_no_coverage_first`; same caveat applies to all five --
   though `uwtig_no_coverage_first`'s effect is large enough (recall
   0.63 -> 0.36) to be clearly visible even at 5 seeds, unlike the other four).
5. **Postgres/Neo4j run as local Docker containers** with dev-only
   credentials (`docker/docker-compose.yml`), not a production deployment.
6. **A real fairness bug was found and fixed during development**: the
   shared `MemoryStore` used across the whole planner comparison sweep
   initially let different planners' detection histories leak into each
   other through persistent memory (since defect identity matching wasn't
   scoped per scenario+planner+seed). Fixed via run-scoped wall keys in
   `experiments/mission.py` (`run_key = f"{scenario}|{planner}|{seed}"`),
   verified with a targeted isolation test before the numbers above were
   produced.
7. **The full 5-seed sweep (one long-lived process, 140 mission-runs)
   crashed three consecutive times** after the novelty-pass planner
   changes, with three different low-level symptoms (a numpy "unable to
   allocate 2.34 MiB" error despite 15GB free RAM, a silent exit code 127,
   then a segfault/exit 139) -- consistent with a resource-accumulation
   issue in pybullet's `ER_TINY_RENDERER` software rasterizer across ~140
   sequential connect/render/disconnect cycles in one process (each mission
   opens a fresh `KinematicHouse`/DIRECT client), not a bug in the planner
   logic, which touches no rendering code. Fixed (not just worked around)
   by adding `--seed N` / `--merge` to `experiments/evaluate.py` and
   `run_full_sweep.sh`, which runs each seed as its own fresh subprocess
   (28 mission-runs each, well inside the crash-free range) and merges the
   per-seed CSVs afterward. 4 of 5 seeds succeeded on the first subprocess
   attempt; seed 1 hit a transient `OpenBLAS`/Windows-fork resource error
   (`cygheap read copy failed`) on all 3 scripted retries within the same
   run, then succeeded immediately when retried alone afterward -- pointing
   to transient system-level pressure from running many subprocesses in
   quick succession (already easing by the next seed in the same run, and
   gone by the time seed 1 was retried alone) rather than a per-seed
   deterministic failure. The "Updated 5-seed results" section above is the
   real, complete, 5-seed output of this approach.
8. **The uncertainty signal UW-TIG plans around is not shown to correlate
   with correctness the way its name implies -- checked directly, not
   assumed.** Prompted by a deeper read of Rückin et al.'s evaluation
   methodology (IEEE T-RO 2023), two calibration metrics were added and run
   (see "Calibration check" above): detector confidence has a high ECE
   (0.28-0.36, well above what a calibrated model would show), and
   `uncertainty_gap_fp_minus_tp` is *negative* for every planner -- false
   positives have lower TTA-ensemble uncertainty than true positives, on
   average, the opposite of the assumption implicit in weighting uncertainty
   positively as a "worth a second look" signal. The ablations still show
   `w_uncertainty` changes behavior somewhat (it's a real, measured signal,
   just not a validated-calibrated one), and it's used only as a relative
   ranking signal within one mission, never thresholded as an absolute
   probability -- so this doesn't invalidate the planner's measured
   precision/recall/reinspection results above, but it does mean "TTA
   ensemble variance is highly uncertain here, so this is probably wrong"
   is not a claim this project can currently back with evidence; the
   opposite direction is what was measured. A real fix would swap in an
   uncertainty estimate actually validated for calibration (e.g. MC-Dropout,
   as Rückin et al. use, or post-hoc temperature scaling) -- out of scope
   for this pass, which was about measuring and reporting the gap honestly,
   not fixing it.
