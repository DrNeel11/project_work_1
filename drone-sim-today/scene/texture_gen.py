"""Parametric wall-texture generator: for each sample, produces a matching
pair of (photorealistic texture, label-mask texture) sharing the exact same
defect geometry. The label-mask texture paints the defect region in a flat,
unique, unlit class color on black -- rendering it through the identical
PyBullet camera pose as the photorealistic texture recovers a pixel-perfect
segmentation polygon for free (no manual annotation, no analytic UV math).

`severity` in [0, ~1.4] scales a defect's physical extent so the same
(seed, center) pair can be re-rendered larger across missions for the
"growing defect" scenario in experiments/scenarios.py.
"""
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
CENTER = SIZE // 2

# Base extents at severity=1.0 (see original scene/make_textures.py, which
# this generalizes with a severity scale + explicit/reproducible center).
TRUNK_BAND = 70
BLOB_EXTENT = 90
LEAK_EXTENT = 80

LABEL_COLOR = {"crack": (255, 40, 40), "corrosion": (40, 220, 40), "leakage": (40, 80, 255)}
CLASS_IDS = {"crack": 0, "corrosion": 1, "leakage": 2}


def _noisy_base(color, rng, noise_amt=8):
    arr = np.full((SIZE, SIZE, 3), color, dtype=np.int16)
    arr += rng.randint(-noise_amt, noise_amt + 1, size=(SIZE, SIZE, 3))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def random_base_color(rng):
    """Wider material variety than the original 3 fixed greys, so the
    trained model doesn't overfit to one wall tone."""
    hue_pick = rng.choice(["grey", "beige", "blue_grey", "concrete"])
    base = {
        "grey": (185, 185, 185),
        "beige": (205, 195, 165),
        "blue_grey": (170, 180, 190),
        "concrete": (195, 192, 180),
    }[hue_pick]
    jitter = rng.randint(-15, 16, size=3)
    return tuple(int(np.clip(c + j, 60, 235)) for c, j in zip(base, jitter))


def _crack_path(rng, center, severity):
    band = int(TRUNK_BAND * severity)
    cx, cy = center
    lo, hi = cx - band, cx + band
    x, y = cx + rng.randint(-10, 11), max(0, cy - band)
    points = [(x, y)]
    branches = []
    y_top = max(0, cy - band)
    y_bot = min(SIZE, cy + band)
    while y < y_bot:
        x += rng.randint(-22, 23)
        y += rng.randint(12, 30)
        x = int(np.clip(x, lo, hi))
        points.append((x, y))
        if rng.random() < 0.35 and len(points) > 2:
            bx, by = points[-2]
            ex = int(np.clip(bx + rng.randint(-28, 29), lo, hi))
            ey = min(y_bot, by + rng.randint(18, 45))
            branches.append(((bx, by), (ex, ey)))
    return points, branches


def _make_crack(rng, center, severity, base_color, width_px=None):
    tex = _noisy_base(base_color, rng)
    mask = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    points, branches = _crack_path(rng, center, severity)
    w = width_px if width_px is not None else max(2, int(3 + 2 * severity))

    tdraw = ImageDraw.Draw(tex)
    mdraw = ImageDraw.Draw(mask)
    for a, b in branches:
        tdraw.line([a, b], fill=(25, 25, 25), width=max(1, w - 1))
        mdraw.line([a, b], fill=LABEL_COLOR["crack"], width=max(3, w + 3))
    tdraw.line(points, fill=(15, 15, 15), width=w)
    mdraw.line(points, fill=LABEL_COLOR["crack"], width=w + 3)

    tex = tex.filter(ImageFilter.GaussianBlur(0.4))
    return tex, mask


def _make_rust(rng, center, severity, base_color):
    tex = _noisy_base(base_color, rng)
    mask = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    tdraw = ImageDraw.Draw(tex, "RGBA")
    mdraw = ImageDraw.Draw(mask, "RGBA")
    n_blobs = max(3, int(4 + 4 * severity))
    extent = int(BLOB_EXTENT * severity)
    cx0, cy0 = center
    for _ in range(n_blobs):
        r = rng.randint(int(18 * severity) + 8, int(38 * severity) + 12)
        jitter = max(1, extent - r)
        cx = cx0 + rng.randint(-jitter, jitter + 1)
        cy = cy0 + rng.randint(-jitter, jitter + 1)
        for i in range(r, 0, -4):
            alpha = int(150 * (1 - i / r))
            col = (120 + rng.randint(-15, 16), 60, 20, alpha)
            tdraw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=col)
            mdraw.ellipse([cx - i, cy - i, cx + i, cy + i], fill=(*LABEL_COLOR["corrosion"], 255))
    tex = tex.filter(ImageFilter.GaussianBlur(1.2))
    return tex, mask


def _make_leak(rng, center, severity, base_color):
    tex = _noisy_base(base_color, rng)
    mask = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    overlay = Image.new("RGBA", tex.size, (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(overlay)
    mdraw = ImageDraw.Draw(mask)
    width = int(rng.randint(45, 70) * severity)
    height = int(rng.randint(180, 320) * min(1.3, severity))
    cx, cy = center
    top = max(0, cy - height // 2)
    bottom = min(SIZE, cy + height // 2)
    poly = [(cx - width // 2, top), (cx + width // 2, top),
            (cx + width // 3, bottom), (cx - width // 3, bottom)]
    tdraw.polygon(poly, fill=(30, 40, 60, 120))
    mdraw.polygon(poly, fill=LABEL_COLOR["leakage"])
    tex = Image.alpha_composite(tex.convert("RGBA"), overlay).convert("RGB")
    tex = tex.filter(ImageFilter.GaussianBlur(1.5))
    return tex, mask


def make_wall_texture(defect_type, rng, severity=1.0, base_color=None, center=None):
    """Returns (texture_img, mask_img, meta). `rng` is a numpy Generator-like
    (np.random.RandomState) for reproducibility. `center` is a (px, py) pixel
    position in the 512x512 texture; if None, one is chosen at random and
    returned in meta so callers can re-use it for a "growing" re-render."""
    if base_color is None:
        base_color = random_base_color(rng)
    if center is None:
        center = (int(rng.randint(SIZE // 2 - 60, SIZE // 2 + 61)),
                  int(rng.randint(SIZE // 2 - 60, SIZE // 2 + 61)))

    if defect_type == "clean":
        tex = _noisy_base(base_color, rng)
        mask = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    elif defect_type == "crack":
        tex, mask = _make_crack(rng, center, severity, base_color)
    elif defect_type == "corrosion":
        tex, mask = _make_rust(rng, center, severity, base_color)
    elif defect_type == "leakage":
        tex, mask = _make_leak(rng, center, severity, base_color)
    else:
        raise ValueError(defect_type)

    meta = {"defect_type": defect_type, "severity": severity, "base_color": base_color, "center": center}
    return tex, mask, meta


if __name__ == "__main__":
    import os

    out = os.path.join(os.path.dirname(__file__), "_texture_preview")
    os.makedirs(out, exist_ok=True)
    rng = np.random.RandomState(3)
    for dtype in ["crack", "corrosion", "leakage", "clean"]:
        for sev in [0.5, 1.0, 1.3]:
            tex, mask, meta = make_wall_texture(dtype, rng, severity=sev)
            tex.save(os.path.join(out, f"{dtype}_s{sev}_tex.png"))
            mask.save(os.path.join(out, f"{dtype}_s{sev}_mask.png"))
    print("wrote previews to", out)
