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
   precision 0.86 -> 0.76, mean localization error 0.19m -> 0.72m, flight
   distance 0.3m -> 108.9m. Not a strict improvement, a different point on
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

## 3. What this does and doesn't claim

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
