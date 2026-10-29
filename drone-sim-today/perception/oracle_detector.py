"""A synthetic 'oracle' detector for testing the planner on its own.

The real YOLO detector cannot see the procedural defects of the *growing* scenario and gives only weak
uncertainty signals, so two of UW-TIG's ideas (uncertainty and growth) cannot be exercised with it. This
detector bypasses perception: it reads the scenario's ground truth, projects the defect into the camera and
returns a detection with controlled noise. It is NOT evidence about real detection quality; it answers a
planner-only question: if detections were clean and the uncertainty and growth signals were real, would the
uncertainty and growth terms change the planner's behaviour or results?

Model (all noise is drawn from the mission's seeded generator, so runs are reproducible):
  * a defect is detected only if its centre projects inside the frame; a detection is missed with probability `miss_prob`
  * true physical size = 0.25 m + 0.55 m x severity, so a defect that grows across missions really gets bigger
  * confidence = 0.35 + 0.5 x min(severity, 1) + N(0, 0.04)
  * uncertainty = std of four extra confidence draws whose spread is 0.03 + 0.20 x (1 - min(severity, 1)),
    i.e. faint defects are more uncertain, as the TTA spread is for the real detector
  * the box side in pixels follows the pinhole camera, so mission.py's ray-casting measures the size back
"""
import numpy as np

import geometry as geo

IMG_W, IMG_H = 320, 240


class OracleDetector:
    needs_context = True

    def __init__(self, miss_prob=0.15):
        self.miss_prob = miss_prob

    def __call__(self, bgr, ctx):
        wall_name = ctx["vp"].wall
        gt = ctx["gt"].get(wall_name)
        if gt is None:
            return []
        rng = ctx["rng"]
        scen = ctx["scenario"]
        centre_tex = scen._centers.get(wall_name)
        if centre_tex is None:
            return []
        wall = ctx["wall"]
        world = geo.texture_uv_to_world(wall, centre_tex[0], centre_tex[1])
        view, proj = geo.drone_camera_matrices(ctx["pos"], ctx["quat"])
        clip = proj @ view @ np.append(world, 1.0)
        if clip[3] <= 1e-6:
            return []
        ndc = clip[:3] / clip[3]
        px = (ndc[0] * 0.5 + 0.5) * IMG_W
        py = (1.0 - (ndc[1] * 0.5 + 0.5)) * IMG_H
        if not (0 <= px < IMG_W and 0 <= py < IMG_H):
            return []
        if rng.rand() < self.miss_prob:
            return []
        sev = float(gt["severity"])
        size_m = 0.25 + 0.55 * sev
        dist = float(np.linalg.norm(np.asarray(ctx["pos"]) - np.asarray(world)))
        focal_px = (IMG_H / 2.0) / np.tan(np.radians(geo.FOV_DEG) / 2.0)
        side = max(8, int(round(size_m / np.sqrt(2) * focal_px / max(dist, 0.3))))
        x = int(round(px - side / 2))
        y = int(round(py - side / 2))
        x, y = max(0, min(IMG_W - 2, x)), max(0, min(IMG_H - 2, y))
        w, h = min(side, IMG_W - x), min(side, IMG_H - y)
        s = min(sev, 1.0)
        conf = float(np.clip(0.35 + 0.5 * s + rng.normal(0, 0.04), 0.1, 0.99))
        spread = 0.03 + 0.20 * (1.0 - s)
        extra = np.clip(conf + rng.normal(0, spread, size=4), 0.0, 1.0)
        uncertainty = float(np.std(np.concatenate([[conf], extra])))
        return [{"bbox": (x, y, w, h), "label": gt["defect_type"], "confidence": conf, "uncertainty": uncertainty}]
