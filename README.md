# Autonomous Drone Utility Inspection — Closed-Loop Perception, Memory & Active Reinspection

A simulated (PyBullet + gym-pybullet-drones) autonomous inspection drone that
closes the loop the underlying research proposal is about: **detect → assess
uncertainty → replan → reinspect**, with a persistent cross-mission defect
memory, and a quantitative comparison against a naive baseline and the
closest base paper (Isler et al. 2016, information-gain NBV).

All project code lives under [`drone-sim-today/`](drone-sim-today/). Full
methodology and results: [`drone-sim-today/RESULTS.md`](drone-sim-today/RESULTS.md).

## What's built

**Perception** — a real YOLOv8n detector (`perception/train_yolo.py`,
`perception/ml_detector.py`), trained on **MBDD2025**
([Zenodo, CC-BY-4.0](https://doi.org/10.5281/zenodo.15622584)), a real
14,471-image UAV building-defect dataset (crack / leakage / abscission /
corrosion / bulge). Detection uncertainty is a test-time-augmentation (TTA)
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

**Planning** (`planning/`) — three planners sharing one candidate-viewpoint
graph (`planning/viewpoints.py`) over the house scene:
- `RandomPlanner` — naive baseline.
- `IslerNBVPlanner` — cost-normalized entropy-based next-best-view, adapted
  from Isler et al. (2016)'s volumetric information-gain formulation to a
  2D wall-surface coverage grid. Deliberately geometry-only, no defect
  semantics — the literature gap the proposal identifies for this base paper.
- `UWTIGPlanner` (**novel**) — Uncertainty-Weighted Temporal Information Gain:
  the same coverage term, plus detection-uncertainty and temporal-growth
  terms sourced from persistent memory, in one weighted utility. Unlike the
  baselines, it can revisit an already-inspected viewpoint when that's where
  the utility is (active reinspection). Two ablations
  (`uwtig_no_uncertainty`, `uwtig_no_temporal`) isolate each term's effect.

**Experiments** (`experiments/`) — a fast kinematic camera sim
(`kinematic_capture.py`, teleport + render, no PID stepping) drives the
statistical comparison across 4 scenarios (`scenarios.py`: static, uncertain,
growing, multiple defects — static/uncertain/multi-defect use real MBDD2025
photos as wall textures directly; growing uses a procedural generator since
a single-timepoint photo dataset has no repeated-visit growth sequence) ×
5 planners × multiple seeds × sequential missions. `evaluate.py` runs the
full sweep and writes `results/comparison.csv` + comparison charts.

**Flagship demo** (`demo_uwtig_flight.py`) — the same closed loop, but flown
for real: PID-controlled physics flight (not a fixed patrol list, not
kinematic teleport), driven live by UW-TIG + the trained detector, across a
sequence of missions, saved as an annotated video.

**Environment & flight quality** (`sim_house.py`, `scene/environment.py`,
`demo_uwtig_flight.py`) — the two-room house (kept as the inspection layout
throughout) is dressed as a utility inspection yard: a procedurally
generated concrete ground texture, an elevated pipe rack, and a small
lattice support tower surround it. Since the house is fully enclosed, the
flagship demo opens with a slow orbiting establishing shot of the whole
yard (otherwise never visible once the drone is inside, wall-facing, for
the actual inspection flight). Flight itself uses ease-in-ease-out
(smoothstep) trajectory interpolation instead of a linear ramp — DSLPIDControl
tracks a moving reference, so a linear ramp has a velocity discontinuity at
both ends of every hop, which reads as jerky — and the third-person chase
camera exponentially smooths its eye/target position instead of snapping to
the drone's instantaneous pose every frame.

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
python datagen/prepare_sdnet.py                  # merges a balanced subsample into datasets/mbdd_yolo/

python -m perception.train_yolo --epochs 30      # trains weights/mbdd_yolov8n/weights/best.pt
```

## Running the comparison

```bash
python -m experiments.evaluate --seeds 5 --budget 16 --missions 3
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
- The trained model is CPU-budget-limited (small epoch count, 320px images).
- Postgres/Neo4j run as local Docker containers with dev-only credentials.
- The "growing defect" scenario is procedurally synthesized (severity scaled
  over missions with known ground truth) since MBDD2025 is single-timepoint.
