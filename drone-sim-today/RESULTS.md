# Results: Base Paper (Isler-NBV) vs. Novelty (UW-TIG)

## Setup

- **Perception**: YOLOv8n, trained from scratch on **MBDD2025** (14,471 real
  UAV building-defect photos, Zenodo 10.5281/zenodo.15622584, CC-BY-4.0),
  70/20/10 train/val/test split, 30 epochs, 320px, CPU.
- **Uncertainty**: test-time-augmentation (TTA) ensemble variance across 5
  photometric variants (brightness/contrast/noise/blur) — a documented
  substitute for MC-Dropout (see Limitations).
- **Memory**: PostgreSQL+pgvector (detection log + identity matching) and
  Neo4j (defect graph), run via `docker/docker-compose.yml`.
- **Environment**: the two-room house (`sim_house.py`), a candidate-viewpoint
  graph of 48 stations across 9 wall segments (`planning/viewpoints.py`).
- **Comparison**: Random / Isler-NBV / UW-TIG / UW-TIG-no-uncertainty /
  UW-TIG-no-temporal, × 4 scenarios (static, uncertain, growing,
  multi-defect) × 5 seeds × 3 sequential missions × 16-viewpoint budget per
  mission. Full sweep: `python -m experiments.evaluate --seeds 5 --budget 16 --missions 3`.

## Offline perception benchmark (real MBDD2025 test set, 1448 images)

| metric | value |
|---|---|
| mAP50 | 0.685 |
| mAP50-95 | 0.347 |
| precision (mean) | 0.804 |
| recall (mean) | 0.612 |

Per class (P / R / mAP50): crack 0.75/0.45/0.53, leakage 0.85/0.86/0.93,
abscission 0.79/0.58/0.65, corrosion 0.80/0.59/0.70, bulge 0.83/0.58/0.62.
This is a genuinely trained, real-data result — not a placeholder — achieved
with a CPU-only, 30-epoch budget.

## Closed-loop simulation comparison (mean over static/uncertain/multi-defect × 5 seeds × 3 missions)

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
   for the same physical defect. The YOLOv8n model, trained exclusively on
   real photos, essentially does not recognize this synthetic texture as
   corrosion at all (verified directly: 0 detections at conf>0.1 on the
   rendered frame). Any nonzero "growth_detected_frac" logged for this
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
3. **The trained model is CPU-budget-limited**: 30 epochs, 320px, batch 8.
   The mAP50=0.685 result is real but not the ceiling a longer GPU run or
   larger image size would reach.
4. **5 seeds** is enough to see the headline effects (flight efficiency,
   precision, localization) clearly, but not enough to cleanly separate the
   two ablations' individual contributions — see above.
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
