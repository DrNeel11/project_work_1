# Autonomous Drone Utility Inspection — Closed-Loop Perception, Memory & Active Reinspection

A simulated (PyBullet + gym-pybullet-drones) autonomous inspection drone that
closes the loop the underlying research proposal is about: **detect → assess
uncertainty → replan → reinspect**, with a persistent cross-mission defect
memory, and a quantitative comparison against a naive baseline and the
closest base paper (Isler et al. 2016, information-gain NBV).

All project code lives under [`drone-sim-today/`](drone-sim-today/). Full
methodology and results: [`drone-sim-today/RESULTS.md`](drone-sim-today/RESULTS.md).
A wider literature comparison (Bircher et al., GATSBI, persistent-monitoring
and uncertainty-aware-planning lines) and the two real bugs found while
extending the planner: [`drone-sim-today/NOVELTY.md`](drone-sim-today/NOVELTY.md).
A polished PDF writeup: [`drone-sim-today/Autonomous_Drone_Inspection_Report.pdf`](drone-sim-today/Autonomous_Drone_Inspection_Report.pdf).

## What's built

**Perception** — a real YOLO detector (`perception/ml_detector.py`), trained
on **MBDD2025** ([Zenodo, CC-BY-4.0](https://doi.org/10.5281/zenodo.15622584)),
a real 14,471-image UAV building-defect dataset (crack / leakage / abscission
/ corrosion / bulge). Two genuinely-trained checkpoints exist: the original
CPU-only baseline (`perception/train_yolo.py` → YOLOv8n, 320px, 30 epochs,
mAP50 0.685) and the current default (`perception/train_yolo_gpu.py` →
YOLOv8s, 640px, 100 epochs, plus ~4x oversampling of the rarest class via
`datagen/oversample_bulge.py` → mAP50 0.884, run on a rented GPU once the
CPU budget was identified as the limiting factor — full before/after numbers
in RESULTS.md). Detection uncertainty is a test-time-augmentation (TTA)
ensemble variance — a documented substitute for MC-Dropout (stock YOLOv8 has
no dropout retained at inference; see Caveats below).

**3D localization** (`geometry.py`) — every 2D detection is ray-cast from the
known camera pose onto the known wall plane to recover a real-world (x, y, z),
using the exact camera convention gym-pybullet-drones' onboard camera uses.

**Persistent defect memory** (`memory/`) — PostgreSQL+pgvector (append-only
detection log + nearest-neighbor appearance/spatial embedding for identity
matching) and Neo4j (the defect identity graph: `(:Defect)-[:OBSERVED_IN]->
(:Mission)`, `-[:LOCATED_ON]->(:Wall)`), run locally via
`docker/docker-compose.yml`. This is the "digital twin" linking a defect's
location, identity, and history across missions.

**Planning** (`planning/`) — planners sharing one candidate-viewpoint
graph (`planning/viewpoints.py`) over the house scene:
- `RandomPlanner` — naive baseline.
- `IslerNBVPlanner` — cost-normalized entropy-based next-best-view, adapted
  from Isler et al. (2016)'s volumetric information-gain formulation to a
  2D wall-surface coverage grid. Deliberately geometry-only, no defect
  semantics — the literature gap the proposal identifies for this base paper.
- `UWTIGPlanner` (**novel**) — Uncertainty-Weighted Temporal Information Gain:
  the same coverage term, plus detection-uncertainty and temporal-growth
  terms sourced from persistent memory, and a persistent-monitoring
  staleness/latency term (adapted from Alamdari, Fata & Smith 2014), in one
  weighted utility selected via a 2-step receding-horizon lookahead
  (adapted from Bircher et al. 2016 and Dhami et al.'s GATSBI) rather than
  pure 1-step greedy — plus a coverage-guarantee phase that visits every
  wall at least once per mission before switching to that utility, fixing a
  recall ceiling that turned out to affect `isler_nbv` too (see RESULTS.md's
  "Coverage-guarantee fix" section for the full before/after and its honest
  trade-off: recall/coverage roughly double, at a real cost to precision,
  localization error, and flight distance). Unlike the baselines, it can
  revisit an already-inspected viewpoint when that's where the utility is
  (active reinspection). Five ablations (`uwtig_no_uncertainty`,
  `uwtig_no_temporal`, `uwtig_no_staleness`, `uwtig_no_coverage_first`,
  `uwtig_no_lookahead`) isolate each added term's effect. See
  [`NOVELTY.md`](drone-sim-today/NOVELTY.md) for the wider literature
  comparison this was checked against, and for two real bugs (a reward-decay
  bug, a viewpoint-geometry coincidence) found and fixed while adding the
  lookahead.

**Experiments** (`experiments/`) — a fast kinematic camera sim
(`kinematic_capture.py`, teleport + render, no PID stepping) drives the
statistical comparison across 4 scenarios (`scenarios.py`: static, uncertain,
growing, multiple defects — static/uncertain/multi-defect use real MBDD2025
photos as wall textures directly; growing uses a procedural generator since
a single-timepoint photo dataset has no repeated-visit growth sequence) ×
8 planners × multiple seeds × sequential missions. Besides
precision/recall/f1/localization-error/flight-distance/coverage/
reinspection-rate, `evaluate.py` also reports two calibration-style metrics
added after a deeper pass through the informative-path-planning literature
(Rückin et al., IEEE T-RO 2023 — see `NOVELTY.md`'s "Metrics" section):
**`ece`** (Expected Calibration Error of the detector's confidence against
empirical accuracy) and **`uncertainty_gap_fp_minus_tp`** (whether the
TTA-ensemble uncertainty UW-TIG's utility weights is actually higher on
wrong detections than right ones — a direct check of whether its central
"uncertainty" signal is informative, not just noise it's chasing).
`evaluate.py` runs the
full sweep and writes `results/comparison.csv` + comparison charts; on
Windows, prefer `run_full_sweep.sh` (runs each seed as its own subprocess
and merges the results), since a single long-lived process running the
full ~140-mission sweep has crashed repeatedly in this environment — see
RESULTS.md's Limitations.

**Flagship demo** (`demo_uwtig_flight.py`) — the same closed loop, but flown
for real: PID-controlled physics flight (not a fixed patrol list, not
kinematic teleport), driven live by UW-TIG + the trained detector, across a
sequence of missions, saved as an annotated video.

**Environment & flight quality** (`sim_house.py`, `scene/environment.py`,
`demo_uwtig_flight.py`) — an **open-air utility yard**, not an enclosed
building: two freestanding equipment structures (Building A, 4 walls;
Building B, 3 walls) ~11m apart with real open sky between them, plus one
real inspection panel each mounted on a decorative pipe rack and lattice
tower (9 walls/panels total), surrounded by a procedurally generated
concrete ground texture and a sky backdrop with a skyline silhouette on the
horizon. Because the yard is open rather than enclosed, the sky and
surrounding structures stay visible for the *entire* flight, not just a
one-off establishing shot. Flight itself uses ease-in-ease-out
(smoothstep) trajectory interpolation instead of a linear ramp — DSLPIDControl
tracks a moving reference, so a linear ramp has a velocity discontinuity at
both ends of every hop, which reads as jerky — and the third-person chase
camera exponentially smooths its eye/target position instead of snapping to
the drone's instantaneous pose every frame. A rendering realism pass
(consistent shadows/lighting, higher-resolution ground/sky textures, and a
real PyBullet texture-tiling bug found and fixed along the way) and an
honest literature-grounded answer to "why not Unity or Unreal" are in
[`drone-sim-today/NOVELTY.md`](drone-sim-today/NOVELTY.md)'s section 5.

## Setup

```bash
cd drone-sim-today
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
git clone https://github.com/utiasDSL/gym-pybullet-drones.git gpd_src
.\venv\Scripts\python.exe -m pip install -e .\gpd_src
```

Persistent memory needs Docker:
```bash
cd docker && docker compose up -d
```

## Getting a trained model

```bash
# 1. Download MBDD2025.zip from https://zenodo.org/records/15622584 into datasets/, then:
cd datasets && unzip MBDD2025.zip
cd .. && python datagen/prepare_mbdd.py         # builds datasets/mbdd_yolo/ (train/val/test split + data.yaml)

# 2. Optional: enrich the "crack" class with SDNET2018 (Maguire et al. 2018,
#    CC-BY-4.0), the public benchmark Inam et al. (2023) -- one of the cited
#    base papers -- combines with their own field data. Behind a bot-check
#    that blocks scripted downloads, so grab it yourself:
#    https://digitalcommons.usu.edu/all_datasets/48/ -> datasets/SDNET2018.zip
python datagen/prepare_sdnet.py                  # merges a balanced subsample into datasets/mbdd_yolo/ (not yet done in this project -- SDNET2018.zip was never actually downloaded, see RESULTS.md)

python -m perception.train_yolo --epochs 30      # CPU baseline -> weights/mbdd_yolov8n/weights/best.pt (mAP50 0.685)

# GPU retrain (needs a CUDA machine -- this project used a rented NVIDIA L4):
python datagen/oversample_bulge.py               # ~4x-oversamples the rarest class (bulge) into datasets/mbdd_yolo/images/train
python -m perception.train_yolo_gpu --epochs 100 --imgsz 640 --model yolov8s.pt
# -> weights/mbdd_yolov8s_gpu/weights/best.pt (mAP50 0.884) -- this is perception/ml_detector.py's current default
```

## Running the comparison

```bash
bash run_full_sweep.sh 5 16 3
# equivalent to, but more reliable than:
# python -m experiments.evaluate --seeds 5 --budget 16 --missions 3
# results/comparison.csv, results/comparison.png
```

## Running the flagship demo

```bash
python demo_uwtig_flight.py --missions 3 --budget 8
# output/uwtig_flythrough.mp4  (third-person, watch it fly + replan)
# output/uwtig_inspection.mp4 (onboard camera + detection/uncertainty overlay)
```

## Caveats (stated plainly, see RESULTS.md for the full writeup)

- Detection uncertainty is TTA ensemble variance, not literal MC-Dropout.
- The original CPU-trained checkpoint was budget-limited (small epoch count,
  320px images) -- resolved by the GPU retrain now used by default, though
  that in turn hasn't been tried past yolov8s/640px (e.g. yolov8m/l, 1280px).
- Even the GPU model isn't perfect: it produced one low-confidence false
  positive on the single genuine background-labeled MBDD2025 test image,
  where the CPU model had none -- a net improvement, not a strictly-dominant
  one (see RESULTS.md's perception section).
- Postgres/Neo4j run as local Docker containers with dev-only credentials.
- The "growing defect" scenario is procedurally synthesized (severity scaled
  over missions with known ground truth) since MBDD2025 is single-timepoint.
- The closed-loop planner comparison (precision/recall/coverage/ECE/etc.)
  can only honestly be compared against the in-house Isler-NBV/Random
  reimplementations in the same table -- no cited paper reports that metric
  set for this kind of planner. The detector itself *is* comparable in kind
  to other defect-detection papers, and on that comparison this project's
  numbers are lower than two narrower/private-dataset papers -- see
  RESULTS.md's "How this compares to numbers reported elsewhere in the
  literature" for the real numbers and why that's not a fully fair fight
  either way.
