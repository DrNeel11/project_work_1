"""Planner-independent detection diagnostic: renders EVERY candidate viewpoint
of every wall (not just the ones a planner happens to pick) and measures,
per (camera resolution, inference size, confidence threshold) setting:

  - view_recall: fraction of (defect-wall, viewpoint) pairs where the correct
    class is detected -- how often a single look succeeds
  - wall_recall: fraction of defect walls where at least one of the wall's 6
    viewpoints detects the correct class -- the ceiling on closed-loop recall
    for a planner that covers every wall
  - fp_per_view: wrong-class or clean-wall detections per rendered view

Run on DEV seeds (default 100-102), never on the seeds RESULTS.md reports
(0-4), so any setting chosen from this output is not tuned on the test set.

Usage: venv python -m experiments.diagnose_detection [--seeds 100 101 102]
"""
import argparse
import collections
import math
import os
import sys
import tempfile

import numpy as np
import pybullet as p
import pybullet_data

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geometry as geo  # noqa: E402
from datagen.prepare_mbdd import CLASS_NAMES  # noqa: E402
from experiments.scenarios import SCENARIO_REGISTRY  # noqa: E402
from perception.ml_detector import _get_model, square_pixels  # noqa: E402
from planning.viewpoints import build_viewpoints  # noqa: E402
from scene.environment import retexture_ground  # noqa: E402
from sim_house import WALL_SEGMENTS, build_house  # noqa: E402

CONFIGS = [  # (name, camera (w, h), inference imgsz)
    ("cam320_inf320", (320, 240), 320),
    ("cam480_inf480", (480, 360), 480),
    ("cam640_inf640", (640, 480), 640),
]
CONF_GRID = [0.15, 0.25, 0.35, 0.5]


class Renderer:
    def __init__(self):
        self.client = p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.client)
        plane = p.loadURDF("plane.urdf", physicsClientId=self.client)
        retexture_ground(self.client, plane)
        self.wall_bodies = build_house(self.client)
        self.wall_by_name = {w["name"]: w for w in WALL_SEGMENTS}

    def set_wall_texture(self, wall_name, path):
        tex = p.loadTexture(path, physicsClientId=self.client)
        p.changeVisualShape(self.wall_bodies[wall_name], -1, textureUniqueId=tex, physicsClientId=self.client)

    def render(self, vp, w, h):
        quat = p.getQuaternionFromEuler([0, 0, math.radians(vp.yaw_deg)])
        view, proj = geo.drone_camera_matrices(vp.pos, quat)
        _, _, rgba, _, _ = p.getCameraImage(
            width=w, height=h, viewMatrix=view.flatten(order="F").tolist(),
            projectionMatrix=proj.flatten(order="F").tolist(), shadow=1,
            lightDirection=[0.6, -0.4, 1.0], renderer=p.ER_TINY_RENDERER, physicsClientId=self.client)
        return np.reshape(rgba, (h, w, 4))[:, :, :3].astype(np.uint8)[:, :, ::-1].copy()

    def close(self):
        p.disconnect(physicsClientId=self.client)


def run(seeds, scenarios, standoffs=None, configs=None):
    global CONFIGS
    if configs:
        CONFIGS = [c for c in CONFIGS if c[0] in configs]
    model = _get_model()
    if standoffs:
        import planning.viewpoints as vpmod
        vpmod.STANDOFFS = standoffs
    viewpoints, _ = build_viewpoints(WALL_SEGMENTS)
    by_standoff_hits = collections.Counter()
    by_standoff_total = collections.Counter()
    # stats[(config, conf, scenario)] -> counters
    view_hits = collections.Counter()
    view_total = collections.Counter()
    fp = collections.Counter()
    n_views = collections.Counter()
    wall_any = collections.defaultdict(set)  # key -> set of (seed, wall) detected
    wall_total = collections.defaultdict(set)

    for scen_name in scenarios:
        for seed in seeds:
            scen = SCENARIO_REGISTRY[scen_name](seed=seed)
            r = Renderer()
            with tempfile.TemporaryDirectory() as td:
                gt = scen.setup_mission(r, 1, td)
                for vp in viewpoints:
                    gt_label = gt.get(vp.wall, {}).get("defect_type")
                    present = gt.get(vp.wall, {}).get("present_classes", set())
                    for cname, (cw, ch), imgsz in CONFIGS:
                        bgr, _ = square_pixels(r.render(vp, cw, ch))
                        res = model.predict(bgr, conf=min(CONF_GRID), imgsz=imgsz, verbose=False)[0]
                        dets = [(CLASS_NAMES[int(b.cls.item())], float(b.conf.item())) for b in res.boxes]
                        for thr in CONF_GRID:
                            key = (cname, thr, scen_name)
                            kept = [lab for lab, c in dets if c >= thr]
                            n_views[key] += 1
                            if gt_label:
                                view_total[key] += 1
                                wall_total[key].add((seed, vp.wall))
                                by_standoff_total[(cname, thr, vp.standoff)] += 1
                                if gt_label in kept:
                                    view_hits[key] += 1
                                    wall_any[key].add((seed, vp.wall))
                                    by_standoff_hits[(cname, thr, vp.standoff)] += 1
                            fp[key] += sum(1 for lab in kept if lab not in present)
            r.close()
            print(f"  done {scen_name} seed={seed}", flush=True)

    print(f"\n{'config':16s} {'conf':>5s} {'scenario':13s} {'view_recall':>11s} {'wall_recall':>11s} {'fp/view':>8s}")
    for cname, _, _ in CONFIGS:
        for thr in CONF_GRID:
            for scen_name in scenarios + ["ALL"]:
                keys = [(cname, thr, s) for s in (scenarios if scen_name == "ALL" else [scen_name])]
                vt = sum(view_total[k] for k in keys)
                vh = sum(view_hits[k] for k in keys)
                wt = sum(len(wall_total[k]) for k in keys)
                wa = sum(len(wall_any[k]) for k in keys)
                nv = sum(n_views[k] for k in keys)
                f = sum(fp[k] for k in keys)
                print(f"{cname:16s} {thr:5.2f} {scen_name:13s} {vh / vt if vt else float('nan'):11.3f} "
                      f"{wa / wt if wt else float('nan'):11.3f} {f / nv if nv else float('nan'):8.3f}")

    print(f"\nsingle-view recall by standoff (defect walls only)")
    for (cname, thr, so), tot in sorted(by_standoff_total.items()):
        print(f"{cname:16s} {thr:5.2f} standoff={so:.1f}m  {by_standoff_hits[(cname, thr, so)] / tot:.3f}  (n={tot})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[100, 101, 102])
    ap.add_argument("--scenarios", nargs="+", default=["static", "uncertain", "multi_defect"])
    ap.add_argument("--standoffs", type=float, nargs="+", default=None)
    ap.add_argument("--configs", nargs="+", default=None)
    args = ap.parse_args()
    run(args.seeds, args.scenarios, args.standoffs, args.configs)
