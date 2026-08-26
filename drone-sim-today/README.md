# Autonomous Drone Utility Inspection — Simulation Prototype

Autonomous flight (real physics + PID control, not scripted teleport) through a
simulated two-room house, with an onboard camera and a defect "sensor" that
flags crack/rust/leak vs. clean walls.

## What's actually built (current status)
- **Flight**: `gym-pybullet-drones` + `DSLPIDControl` — closed-loop PID control
  reacting to real rigid-body physics, not position teleportation.
- **Environment**: `sim_house.py` — a two-room house (4m room -> 1m doorway ->
  2.6m room), 8 textured wall panels, autonomous patrol of all of them.
- **Perception**: `detect.py` — classical OpenCV heuristics (threshold +
  contour-shape for crack/leak, HSV color for rust). **Not a trained model** —
  this is a placeholder tuned to the synthetic textures in `scene/`, standing
  in for a real YOLOv8-seg model until a labeled dataset exists.
- **Real-hardware bridge**: `tello_fly.py`, written against `djitellopy` for a
  DJI Tello — **untested**, no physical drone has been flown yet.

## What's NOT built yet
- Uncertainty scoring / active re-inspection (the actual novel claim of the
  underlying research proposal — perception driving flight replanning, not
  just flight-then-detect)
- 3D defect localization (ground-truth pose is available in sim, nothing
  projects 2D detections into 3D world coordinates yet)
- Persistent memory / temporal comparison across sessions
- A trained perception model (`detect.py` is classical CV, not ML)
- Any real-world flight (`tello_fly.py` is unflown)

## Setup
```bash
python -m venv venv
# Windows
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# gym-pybullet-drones is not on PyPI — clone and install it separately:
git clone https://github.com/utiasDSL/gym-pybullet-drones.git gpd_src
.\venv\Scripts\python.exe -m pip install -e .\gpd_src
```

## Running the demos
```powershell
.\run_house.bat --no-live      # two-room house patrol (primary demo)
.\run_gpd.bat --no-live        # earlier single-corridor version
```
Drop `--no-live` for a live OpenCV preview window, add `--gui-sim` to also
watch the PyBullet physics viewport.

`run_house.bat` produces two videos in `output/`:
- `house_flythrough.mp4` — third-person chase-cam, watch it actually fly
- `inspection_run_house.mp4` — onboard camera + detection overlay per wall

## Real hardware (DJI Tello, untested)
```powershell
.\venv\Scripts\python.exe tello_fly.py          # connection/battery check only, no takeoff
.\venv\Scripts\python.exe tello_fly.py --fly    # actually flies the patrol in PATROL
```
Calibrate the `rotate`/`forward` values in `tello_fly.py` against your actual
room before flying — the defaults are placeholders. Prop guards on, clear open
space, battery >30%.
