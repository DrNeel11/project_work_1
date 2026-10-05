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
# Long side of the generated texture. The wall camera sees only ~1 m of a
# 2.6-4 m wall at close standoff, so a 512 px texture (the procedural
# generator's SIZE) is magnified ~3x into visible blocky pixels -- an
# artifact no real camera would see. Ground-truth `center` stays expressed
# in geometry.texture_uv_to_world's 512-normalized texture units regardless.
TEX_LONG_SIDE = 1536
GT_TEX_UNITS = 512

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


def make_wall_texture(defect_type, rng, severity=1.0, base_color=None, center=None, aspect=1.0):
    """`aspect` is the target wall's width/height. The photo is cropped to
    that aspect (not to a square later stretched across a 4 m x 2.4 m wall,
    which smeared every defect ~1.7x horizontally), so photo pixels land
    square on the wall."""
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
    crop_w, crop_h = (iw, iw / aspect) if iw / aspect <= ih else (ih * aspect, ih)
    bx, by = cx * iw, cy * ih
    x0 = float(np.clip(bx - crop_w / 2, 0, max(0.0, iw - crop_w)))
    y0 = float(np.clip(by - crop_h / 2, 0, max(0.0, ih - crop_h)))
    out_w, out_h = ((TEX_LONG_SIDE, round(TEX_LONG_SIDE / aspect)) if aspect >= 1
                    else (round(TEX_LONG_SIDE * aspect), TEX_LONG_SIDE))
    tex = img.crop((round(x0), round(y0), round(x0 + crop_w), round(y0 + crop_h))).resize(
        (out_w, out_h), Image.LANCZOS)

    if center is None:
        tex_cx = int(np.clip((bx - x0) / crop_w * GT_TEX_UNITS, 0, GT_TEX_UNITS - 1))
        tex_cy = int(np.clip((by - y0) / crop_h * GT_TEX_UNITS, 0, GT_TEX_UNITS - 1))
        center = (tex_cx, tex_cy)
        _photo_by_center[(defect_type, center)] = (base, cx, cy, w, h)

    meta = {"defect_type": defect_type, "severity": severity, "base_color": base_color,
            "center": center, "source_image": base,
            "present_classes": _classes_in_crop(base, iw, ih, x0, y0, crop_w, crop_h) | {defect_type}}
    return tex, None, meta


def _classes_in_crop(base, iw, ih, x0, y0, crop_w, crop_h):
    """Every class with a labeled box centered inside the crop. 16% of
    MBDD2025 test photos carry more than one class, so a photo picked for
    `crack` can genuinely also contain labeled `abscission` -- detecting it is
    a correct detection, not a false positive, and evaluate.py must know."""
    present = set()
    for line in open(os.path.join(LBL_DIR, base + ".txt")):
        parts = line.split()
        if not parts:
            continue
        bcx, bcy = float(parts[1]) * iw, float(parts[2]) * ih
        if x0 <= bcx <= x0 + crop_w and y0 <= bcy <= y0 + crop_h:
            present.add(CLASS_NAMES[int(parts[0])])
    return present


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "_mbdd_preview")
    os.makedirs(out, exist_ok=True)
    rng = np.random.RandomState(0)
    for dtype in CLASS_NAMES:
        tex, _, meta = make_wall_texture(dtype, rng)
        tex.save(os.path.join(out, f"{dtype}.png"))
        print(dtype, meta)
