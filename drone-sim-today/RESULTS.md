# Results: Base Paper (Isler-NBV) vs. Novelty (UW-TIG)

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
- **Environment**: the two-room house (`sim_house.py`), a candidate-viewpoint
  graph of 54 stations across 9 wall segments (`planning/viewpoints.py`) --
  see the status note below the "Original 5-seed table" for why this count
  differs from that table's 48.
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

## Flagship real-flight demo

`python demo_uwtig_flight.py --missions 3 --budget 8 --scenario multi_defect`
— real PID-controlled physics flight (not a fixed patrol, not kinematic
teleport), driven live by UW-TIG + the trained detector, across 3 sequential
missions over the multi-defect real-photo scenario (six walls, three real
defect classes). Outputs `output/uwtig_flythrough.mp4` (third-person — opens
with a wide orbiting establishing shot of the utility yard, since the house
is fully enclosed and the drone never sees it again once flying, then
follows the drone with a smoothed chase cam through smoothstep-eased
flight) and `output/uwtig_inspection.mp4` (onboard camera +
detection/confidence/uncertainty overlay).

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
4. **5 seeds** is enough to see the headline effects (flight efficiency,
   precision, localization) clearly, but not enough to cleanly separate the
   four ablations' individual contributions — see above (originally two
   ablations; the novelty pass added `uwtig_no_staleness` and
   `uwtig_no_lookahead`, same caveat applies to all four).
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
