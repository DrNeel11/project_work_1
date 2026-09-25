"""Real-photo defect provider for experiments/scenarios.py's static/
uncertain/multi_defect scenarios: uses an actual MBDD2025 photo (TEST split
only -- held out of training, so the closed-loop sim measures genuine
generalization, not memorized appearance) as the wall texture itself
(square-cropped around the defect, then resized), rather than a synthetic
composite -- avoids the domain shift of pasting an out-of-context crop onto
a flat synthetic base. Ground truth "center" is the defect's real bounding
box center, transformed through the same crop+resize into texture-pixel
space, so geometry.texture_uv_to_world localization ground truth still
works exactly like the procedural provider.

Same call shape as scene/texture_gen.make_wall_texture, so
experiments/scenarios.py can use either interchangeably:
    make_wall_texture(defect_type, rng, severity=1.0, base_color=None, center=None)
    -> (texture_img, None, meta)

`center` doubles as the cache key scenarios.py uses to keep the SAME wall
showing the SAME photo across a scenario's mission sequence (see
_photo_by_center below) -- required for cross-mission identity matching in
memory/store.py to see a consistent physical position.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datagen.prepare_mbdd import CLASS_NAMES  # noqa: E402
from scene.texture_gen import SIZE, _noisy_base, random_base_color  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "datasets", "mbdd_yolo", "images", "test")
LBL_DIR = os.path.join(ROOT, "datasets", "mbdd_yolo", "labels", "test")

TARGET_AREA_FRAC = 0.12  # prefer a defect box around this fraction of the frame

_index_cache = None
_photo_by_center = {}


def _build_index():
    """{class_name: [(basename, cx,cy,w,h in normalized yolo coords), ...]}"""
    global _index_cache
    if _index_cache is not None:
        return _index_cache
    index = {c: [] for c in CLASS_NAMES}
    for fname in os.listdir(LBL_DIR):
        base = fname[:-4]
        for line in open(os.path.join(LBL_DIR, fname)):
            parts = line.split()
            if not parts:
                continue
            cls_id = int(parts[0])
            cx, cy, w, h = (float(v) for v in parts[1:5])
            index[CLASS_NAMES[cls_id]].append((base, cx, cy, w, h))
    _index_cache = index
    return index


def _pick_photo(defect_type, rng, severity=1.0):
    """severity scales the target bbox-area fraction: low severity picks a
    smaller, fainter-in-frame real instance (used by the "uncertain"
    scenario), high severity picks a clearly-visible one."""
    candidates = _build_index()[defect_type]
    if not candidates:
        raise ValueError(f"no test-split examples for class {defect_type!r}")
    idx = rng.choice(len(candidates), size=min(40, len(candidates)), replace=False)
    sampled = [candidates[i] for i in idx]
    target = TARGET_AREA_FRAC * max(0.15, min(1.0, severity))
    return min(sampled, key=lambda c: abs(c[3] * c[4] - target))


def make_wall_texture(defect_type, rng, severity=1.0, base_color=None, center=None):
    if base_color is None:
        base_color = random_base_color(rng)

    if defect_type == "clean":
        canvas = _noisy_base(base_color, rng)
        if center is None:
            center = (int(rng.randint(SIZE // 2 - 60, SIZE // 2 + 61)),
                      int(rng.randint(SIZE // 2 - 60, SIZE // 2 + 61)))
        return canvas, None, {"defect_type": "clean", "severity": 0.0,
                               "base_color": base_color, "center": center}

    cache_key = (defect_type, center)
    if center is not None and cache_key in _photo_by_center:
        base, cx, cy, w, h = _photo_by_center[cache_key]
    else:
        base, cx, cy, w, h = _pick_photo(defect_type, rng, severity=severity)

    img = Image.open(os.path.join(IMG_DIR, base + ".jpg")).convert("RGB")
    iw, ih = img.size
    side = min(iw, ih)
    bx, by = cx * iw, cy * ih
    x0 = int(np.clip(bx - side / 2, 0, max(0, iw - side)))
    y0 = int(np.clip(by - side / 2, 0, max(0, ih - side)))
    square = img.crop((x0, y0, x0 + side, y0 + side)).resize((SIZE, SIZE))

    if center is None:
        tex_cx = int(np.clip((bx - x0) / side * SIZE, 0, SIZE - 1))
        tex_cy = int(np.clip((by - y0) / side * SIZE, 0, SIZE - 1))
        center = (tex_cx, tex_cy)
        _photo_by_center[(defect_type, center)] = (base, cx, cy, w, h)

    meta = {"defect_type": defect_type, "severity": severity, "base_color": base_color,
            "center": center, "source_image": base}
    return square, None, meta


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "_mbdd_preview")
    os.makedirs(out, exist_ok=True)
    rng = np.random.RandomState(0)
    for dtype in CLASS_NAMES:
        tex, _, meta = make_wall_texture(dtype, rng)
        tex.save(os.path.join(out, f"{dtype}.png"))
        print(dtype, meta)
