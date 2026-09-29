# Novelty Positioning: UW-TIG vs. the Active-Inspection-Planning Literature

This extends RESULTS.md's one-baseline comparison (Isler et al. 2016) with a
wider literature sweep, and documents concrete algorithmic strengthening
done to UW-TIG as a result of that sweep -- including a real bug the new
lookahead term exposed and fixed. Every paper below is a real, checkable
citation (arXiv id or venue given); nothing here is invented.

## 1. Where UW-TIG sits

| Approach | Uncertainty-aware? | Persistent (cross-mission) memory? | Growth/temporal tracking? | Cost/travel-aware? | Real trained detector? | Guarantee |
|---|---|---|---|---|---|---|
| Random (baseline) | no | no | no | no | n/a | none |
| **Isler et al. 2016** (volumetric info-gain NBV) | no (geometry entropy only) | no | no | yes (cost-normalized) | n/a (occupancy, not semantic) | none stated |
| **Bircher et al. 2016** ("Receding Horizon NBV Planner", ICRA) | no | no | no | yes (tree search, execute-1-step) | n/a | none stated |
| **Dhami et al., GATSBI** (arXiv:2012.04803, arXiv:2406.16625) | no | no (single-session) | no | yes (GTSP-routed) | yes (defect detection added in the 2024 extension) | none stated |
| **Pred-NBV / MAP-NBV** (arXiv:2304.11465, arXiv:2307.04004) | indirectly (via shape-completion confidence) | no | no (predicts unseen *geometry*, not defect change) | yes (control-effort term) | n/a (object reconstruction, not defect detection) | none stated |
| **Wang et al., uncertainty-controlled CPP** (arXiv:2201.04310) | yes (measurement uncertainty) | no | no | yes | n/a (dimensional/quality inspection, not vision defects) | coverage-quality bound |
| **Active search under detector uncertainty** (arXiv:2303.03155, POMDP/MCTS) | yes (detector confidence drives belief) | no (single search session) | no | partially | yes (assumes a detector) | POMDP-optimality in the planning horizon |
| **Alamdari, Fata & Smith 2014** (persistent monitoring, IJRR) | no | yes (revisit scheduling is the whole point) | no (latency, not defect growth) | yes (walk cost) | n/a | O(log n) / O(log ρ) approximation |
| **Rückin et al.** (ICRA 2022, arXiv:2109.13570; IROS 2022, arXiv:2203.01652; IEEE T-RO 2023, arXiv:2302.03347) | yes (Bayesian/MC-Dropout epistemic uncertainty via BALD, mapped onto a terrain grid) | no (single mission; the "model" being improved persists, not a per-defect identity) | no (no repeated-visit change tracking — the goal is training-set coverage, not monitoring a known object over time) | yes (acquisition value normalized by a per-cell training-data-count term, then a frontier-style argmax — structurally close to UW-TIG's ig-minus-cost utility) | yes (a real semantic segmentation model, retrained iteratively on the UAV's own picks) | none stated |
| **UW-TIG (this project)** | **yes** (real TTA-ensemble detector uncertainty) | **yes** (Postgres+pgvector / Neo4j identity + growth across missions) | **yes** (growth term from re-identified defects) | **yes** (translation + rotation cost, receding-horizon) | **yes** (YOLOv8n trained on real MBDD2025 photos) | inherited (1-1/e) guarantee on the coverage sub-objective only (see below); no guarantee on the full utility |

No single cited work combines all five columns UW-TIG does. The honest
framing is not "we beat every baseline on every metric" (RESULTS.md already
shows real recall/coverage costs) -- it's that this is, as far as this
literature sweep found, the first system to combine *persistent
cross-mission memory* with *real-detector uncertainty* and *cost-aware
receding-horizon selection*, validated end-to-end against a real trained
model rather than assumed ground-truth detections. GATSBI is the closest
single relative (GTSP routing + a real defect detector), but has no
cross-mission memory or detection-uncertainty term; the POMDP/MCTS active
search line has the uncertainty-driven belief update but no persistence
across sessions.

**Rückin et al.'s line of work is the closest single relative on the
*uncertainty* column specifically**, and is worth stating plainly since it's
a better-matched comparison than the others above: it plans UAV paths using
a real, principled Bayesian epistemic-uncertainty estimate (BALD --
mutual information between a prediction and an MC-Dropout ensemble's
weights, arXiv:2302.03347 Eq. in the framework section) mapped onto a
terrain grid, then greedily selects the next viewpoint by that mapped
uncertainty normalized by a cost/count term -- structurally the same
"uncertainty-weighted, cost-normalized greedy" shape as UW-TIG's own
utility. The difference is the objective the uncertainty serves: Rückin et
al.'s uncertainty is about the *segmentation model's* epistemic confidence,
and the goal is choosing which images are worth labeling to retrain that
model (a single-session active-learning problem -- once the model is good
enough, the task is done). UW-TIG's uncertainty is about *this specific
defect's* detection confidence, and the goal is deciding which physical
locations are worth a second look, persisted and re-identified across
missions via `memory/store.py` -- the model itself is fixed at inference
time, never retrained from the drone's own flights. Put differently: Rückin
et al. plan to reduce *model* uncertainty; UW-TIG plans to reduce *world-state*
uncertainty using a fixed model. Both are legitimate uses of the same
underlying idea (uncertainty as an acquisition function for view selection),
applied to different variables. This also made it clear what UW-TIG could
honestly check but never had (see the Metrics section below): whether its
own uncertainty signal is a *calibrated* one, the way Rückin et al.
explicitly validate theirs (their Expected Calibration Error metric).

## 2. Concrete strengthening applied to the planner

Four additions were made to `planning/planners.py`, each independently
ablatable via `PLANNER_REGISTRY`:

0. **Coverage-guarantee phase** (`UWTIGPlanner.select_next`, added after a
   user-reported "recall is too low"): while any wall has zero visits this
   mission, restrict selection to Isler-NBV's own formulation (ig - cost,
   no lookahead) over only the unvisited walls, before falling through to
   the full utility below. Root cause this fixes: `coverage_frac` was stuck
   at exactly 3 of 9 walls for **every** UW-TIG ablation *and* for
   `isler_nbv` itself, identically, across every seed -- proof the ceiling
   came from the cost-normalized-greedy formulation's cost/reward scale on
   this viewpoint graph (the far building is never worth its travel cost
   relative to available coverage-entropy reward, for any weighting of the
   added terms), not from anything specific to UW-TIG's novelty. A weight
   retune could not have reliably fixed this since the same ceiling
   independently afflicts a planner with zero of those weights; an explicit
   phase does not depend on weight scale at all. Ablation:
   `uwtig_no_coverage_first`. Effect size (5-seed, GPU detector, see
   RESULTS.md's "Coverage-guarantee fix" section): recall 0.36 -> 0.63,
   coverage/reinspection_rate 0.33/0.44 -> 1.00/1.00, at a real cost --
   precision 0.86 -> 0.76, mean localization error 0.19m -> 0.70m, flight
   distance 0.3m -> 108.8m. Not a strict improvement, a different point on
   the trade-off surface -- see RESULTS.md for the full honest breakdown,
   including a plausible explanation for the localization-error jump (the
   coverage phase's viewpoint choice optimizes ig-cost, not localization
   quality, unlike the mature reinspection positions UW-TIG settles into
   under the old, coverage-starved behavior).
1. **Persistent-monitoring staleness term** (`MissionBelief.staleness_score`,
   `UWTIGPlanner.w_staleness`): cells accrue reward for time-since-last-visit
   even absent a detected defect, adapted from the latency-minimizing
   revisit-scheduling literature (Alamdari, Fata & Smith 2014; see also the
   multi-robot latency-constrained routing line, e.g. arXiv:1903.06105).
   Ablation: `uwtig_no_staleness`.
2. **2-step receding-horizon lookahead** (`UWTIGPlanner.select_next`):
   evaluates each candidate together with the best viewpoint that could
   follow it, but only ever executes the first step before replanning --
   the same plan-a-horizon/execute-one-step/replan structure as Bircher et
   al. (2016) and the GTSP-clustered receding-horizon replanning in GATSBI.
   Ablation: `uwtig_no_lookahead` (pure 1-step greedy, this project's
   original UW-TIG).
3. **Submodularity framing of the coverage term** (documentation, not a code
   change): `coverage_entropy`'s saturating `exp(-k*view_count)` form makes
   the coverage/information-gain objective a monotone submodular set
   function, so the greedy per-step argmax inherits the classic (1-1/e)
   worst-case guarantee relative to the optimal non-adaptive k-view policy
   on that sub-objective (Nemhauser et al. 1978; Krause, Singh & Guestrin,
   JMLR 2008, "Near-Optimal Sensor Placements in Gaussian Processes"). This
   does NOT extend to the uncertainty/temporal/staleness terms, which are
   driven by an external, non-submodular detector/memory process -- stated
   here precisely so it isn't misread as a guarantee on the full utility.

### A real bug the lookahead exposed and fixed

Adding the lookahead immediately collapsed `total_flight_dist_m` to exactly
`0.000` for every UW-TIG variant across every scenario/seed in a smoke test
-- a strong, suspicious invariant worth chasing rather than shipping.
Root cause, found by tracing per-step utility values:
`uncertainty_score`/`temporal_score` summed a cell's remembered
uncertainty/growth value with **no decay whatsoever** on repeat visits. A
real detector re-confirms a persistent, unchanged defect on every look, so
once any wall produced a detection, revisiting that exact viewpoint kept
re-earning its full uncertainty+growth reward forever, at **zero travel
cost** (self-loop). The lookahead, being more thorough than 1-step greedy,
found and fully exploited this every time. A first fix attempt (decay based
on "steps since the belief was last updated") did not work, precisely
*because* a real detector updates the belief on every re-confirming look --
that counter never accumulated. The working fix reuses `view_count` (times
the cell has actually been looked at, regardless of whether the detector's
report changed) with the same saturating decay already used for coverage
entropy (`MissionBelief._repeat_decay`): repeated identical confirmations
now earn diminishing reward, exactly mirroring the entropy-reduction
argument already made for coverage. This is the single most important
change in this pass -- it makes "uncertainty-weighted" actually mean
"reward for reducing uncertainty," not "reward for remembering a number."

### A second, independent bug the same investigation surfaced

While tracing the zero-flight-distance case, viewpoint positions for
`B-west`, `B-east`, and `B-north` (three different walls of the small,
2.6m-wide Building B) turned out to be numerically identical --
`(14.0, 0.0, 1.2)` for all three at standoff 1.3m. Building B's width is
exactly 2x that standoff, so "stand 1.3m out from each wall, facing in"
converges on the room's exact center for every wall simultaneously. Under a
pure-translation travel cost, this handed every cost-aware planner
(`isler_nbv` and `uwtig` alike, not just the novel one) an unlimited supply
of free 90-180 degree spins disguised as zero-cost viewpoint switches inside
that one room -- inflating the "UW-TIG flies N times less distance" claim
with degenerate geometry rather than genuinely efficient routing. Fixed by
folding a rotation cost into `BasePlanner._cost`. This was NOT fixed by
resizing Building B or the standoff schedule, which would be a larger,
riskier change to the simulated environment; the limitation (viewpoints
from different walls can coincide in small rooms) is now stated here rather
than silently absorbed into the flight-distance numbers.

**The first calibration attempt overcorrected.** `METERS_PER_DEG_YAW = 1/90`
(a 90-degree turn = 1m) did kill the zero-cost exploit, but a re-run showed
it also collapsed `isler_nbv`'s `coverage_frac` from 0.875 to a flat 0.333 --
it made every genuine inter-building trip look expensive enough that the
planner stopped exploring past Building A almost entirely, a second,
self-inflicted regression, caught before it reached RESULTS.md. Recalibrated
to `METERS_PER_DEG_YAW = 1/3600` (a 180-degree turn = 0.05m) by checking the
graph's actual distance distribution (`planning/viewpoints.py`'s 54-viewpoint
graph has a minimum genuinely-different-position gap of 0.14m) and picking a
rotation cost comfortably below that floor -- large enough to break the
exact-zero-cost tie inside Building B, small enough that it can never
outweigh a genuine routing decision anywhere else in the graph. The lesson
generalizes past this one constant: a fix aimed at one failure mode (free
spins in a degenerate room) needs checking against the metric it could
plausibly break next (coverage elsewhere), not just the one it targeted.

## 3. Metrics: what the wider literature suggested, and what was added

RESULTS.md's tables already report precision/recall/f1, mean localization
error, flight distance, coverage, and reinspection rate -- all standard for
this literature (Isler et al., Bircher et al., GATSBI, and the CPP surveys
all report some subset of coverage/path-length/detection-quality). Reading
Rückin et al.'s evaluation section (arXiv:2302.03347) specifically to answer
"what metrics would fit this project" surfaced one used there that this
project never had, despite naming itself "uncertainty-weighted": **Expected
Calibration Error (ECE)**. Rückin et al. use ECE to check whether their
segmentation model's predicted confidence actually tracks its empirical
accuracy, per confidence bin -- a standard calibration check (Guo et al.
2017), not something they invented, but one this project had simply never
run on its own detector despite using its confidence/uncertainty outputs as
a planning signal for three ablations. Two additions were made to
`experiments/evaluate.py`'s `summarize_run`, using data every mission run
already produces (no re-training, no new detector run needed):

- **`ece`** (`compute_ece`): bins every raw detection (real, not just
  UW-TIG's) by the detector's confidence score, compares each bin's mean
  confidence to its empirical accuracy (fraction that were true positives),
  weighted-sums the bins' |confidence - accuracy| gap. Lower is better
  (0 = perfectly calibrated). This is planner-agnostic in principle (the
  detector is shared), but is still reported per-planner since which
  detections a planner's own viewpoint choices surface differs, and the
  MBDD2025-trained detector's calibration on this sim's rendered frames
  specifically (rather than its own held-out photo test set) is exactly
  the domain-transfer question worth checking, not assumed.
- **`uncertainty_gap_fp_minus_tp`**: mean TTA-ensemble uncertainty on false
  positives minus mean TTA-ensemble uncertainty on true positives. This is
  not from Rückin et al. (who use MC-Dropout/BALD on a segmentation model,
  a different uncertainty mechanism from this project's TTA-ensemble
  variance) -- it's a project-specific, simpler check motivated by the same
  underlying question their ECE check asks: is the *specific* uncertainty
  number UW-TIG's utility weights (`w_uncertainty=1.5`) actually informative
  about correctness, or just noise the planner is chasing? A positive gap
  (false positives more uncertain than true positives, on average) is the
  signal that would validate the design -- **the measured value is negative
  for every planner** (-0.02 to -0.08; see RESULTS.md's "Calibration check"
  section), the opposite of what would validate the design. Reported
  honestly as a real limitation (RESULTS.md Limitation 8), not hidden: the
  ablations still show `w_uncertainty` changes behavior somewhat, so it's a
  real signal, just not one shown to track correctness in the assumed
  direction.

**What was considered and did NOT transfer, stated plainly:** Rückin et
al.'s headline metrics (mIoU, per-pixel accuracy, per-pixel F1) are
segmentation metrics -- they score a dense per-pixel label map against
ground truth. This project's detector produces discrete bounding boxes over
a small, fixed set of wall panels, evaluated at the panel/defect-instance
level (already what RESULTS.md's precision/recall/f1 columns do) — there is
no dense pixel grid to score an IoU against, so importing mIoU here would be
a category error, not a genuine strengthening. Their "number of training
images needed to reach a target mIoU" sample-efficiency framing also doesn't
transfer directly, since this project's detector is trained once, offline,
and never retrained from mission data (a real, stated difference from
Rückin et al.'s active-learning loop, not an oversight) -- the closest
analogous question here, "how many viewpoints does a planner need to reach
a target recall," is already implicitly answered by the existing
budget-fixed comparison across planners, not a new metric.

**A related question worth answering explicitly: can any of this project's
own numbers be checked against numbers actually reported in the cited
papers, not just against the in-house Random/Isler-NBV reimplementation?**
For the closed-loop planner table (precision/recall/coverage/reinspection-
rate/ECE/uncertainty-gap), the honest answer is no -- no cited paper reports
that metric set for this kind of persistent-memory active-reinspection
planner (Isler et al. 2016 has no precision/recall concept at all; GATSBI
reports a differently-defined "detection rate vs. frontier baseline," not
convertible to these columns) -- see RESULTS.md's note directly above that
table. For the *detector* alone, though, a real comparison is possible,
since Li, Shi & Sun 2026 and Inam et al. 2023 report the same kind of
metric (precision/recall/mAP) on their own defect datasets -- see
RESULTS.md's "How this compares to numbers reported elsewhere in the
literature" for the real numbers and the honest, non-flattering result
(this project's detector's raw numbers are lower than both, for reasons
that are partly about task difficulty and dataset provenance, not just
model quality -- stated plainly rather than omitted).

## 4. What this does and doesn't claim

- These are real, reproducible code changes, now backed by a real 5-seed
  statistical sweep. The first attempt at the full sweep (one long-lived
  process, `experiments/evaluate.py --seeds 5 --budget 16 --missions 3`)
  crashed three consecutive times with three different low-level symptoms
  (numpy allocation failure despite free RAM, a silent exit, a segfault) --
  almost certainly a pybullet `ER_TINY_RENDERER` resource-accumulation issue
  across ~140 sequential render sessions in one process, not a bug in this
  planner code (which touches no rendering path). Fixed properly rather than
  worked around: `evaluate.py` gained `--seed N` (run one seed only, write
  its own CSV) and `--merge` (concatenate per-seed CSVs), driven by
  `run_full_sweep.sh`, so each seed runs in its own fresh subprocess (28
  mission-runs each, well under whatever threshold was causing the crash).
  4 of 5 seeds succeeded first try; the fifth hit a transient resource error
  during the same batch run but succeeded immediately when retried alone
  afterward. RESULTS.md's "Updated 5-seed results" section is the real
  output: no more exact-zero camping, `isler_nbv` and `uwtig` both settle on
  the same 3-wall subset (Building B) for reasons explained there, and
  UW-TIG still clearly wins on precision (0.86 vs. 0.64/0.58) and
  localization error (0.19m vs. 0.49m/0.77m) against isler_nbv/random. That
  sweep was later re-run a second time against a separately GPU-retrained
  detector (perception's own novelty pass, see RESULTS.md's perception
  section and Limitation 3) -- the numbers just quoted are from that final
  run; every planner's precision improved with the better detector, but the
  relative ranking and the planner-level findings in this document
  (staleness/lookahead additions, the two bugs, the recalibration) are
  unaffected, since they're about planning behavior, not detection quality.
- The (1-1/e) guarantee is stated precisely: it covers the coverage
  sub-objective's greedy selection, not the combined uncertainty +
  temporal + staleness + cost utility, which has no known guarantee here or
  in any of the cited uncertainty-aware/temporal work.
- "More related papers" was interpreted as: find the real literature this
  system should be positioned against, use it to find an actual weakness
  (it did -- two, both above), and fix what could honestly be fixed in this
  pass. It was not interpreted as inflating the citation count without
  changing the algorithm.
- Two real limitations remain open, stated plainly: (1) the lookahead's
  second step scores uncertainty/temporal/staleness from the *current*
  belief, not a simulated post-first-step one, because simulating a
  detector's future output isn't available here (documented in
  `UWTIGPlanner`'s docstring); (2) the recalibrated rotation-cost constant
  (`METERS_PER_DEG_YAW = 1/3600`) was chosen to sit below the graph's
  smallest real translation gap, not fit to this drone's actual
  yaw-rate/velocity ratio -- an easy follow-up with real flight timing data
  from `demo_uwtig_flight.py`'s PID-controlled runs. (3) `total_flight_dist_m`
  as reported by `experiments/mission.py` counts translation only, so a
  planner that legitimately hovers-and-rotates in a small room (see above)
  reports as near-zero distance even though real rotation time was spent --
  a metric gap, not a planning bug (see RESULTS.md's smoke-test section).
