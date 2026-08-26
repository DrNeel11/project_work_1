"""Generate synthetic wall textures for the demo scene.

Zero-network dependency stand-in for real campus photos. Swap files in
scene/ with real photos later without changing any other code.
"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = os.path.dirname(__file__)
SIZE = 512
CENTER = SIZE // 2
# The narrowest camera crop across the demo scenes is ~177px (room A's 4m
# house walls at 1.2m standoff) out of this 512px texture, i.e. +/-88px
# from center. Every defect feature's full extent (not just its center or
# start point) is kept within CENTER +/- 65 so it survives that crop with
# ~20px of margin on each side.
TRUNK_BAND = 55   # crack trunk/branch clamp
BLOB_EXTENT = 65  # rust: center jitter + max radius
LEAK_EXTENT = 55  # leak: center jitter + max half-width


def _base_wall(color, noise_amt=8):
    img = Image.new("RGB", (SIZE, SIZE), color)
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            r, g, b = px[x, y]
            n = random.randint(-noise_amt, noise_amt)
            px[x, y] = (max(0, min(255, r + n)),
                        max(0, min(255, g + n)),
                        max(0, min(255, b + n)))
    return img


def make_clean(path, color):
    img = _base_wall(color)
    img.save(path)


def make_crack(path, color):
    # Kept within the central band of the canvas: on a wide house-scale
    # wall, the drone's camera only sees a crop centered on the wall
    # midpoint, so a defect drawn near the image edges would be invisible.
    img = _base_wall(color)
    draw = ImageDraw.Draw(img)
    lo, hi = CENTER - TRUNK_BAND, CENTER + TRUNK_BAND
    x, y = random.randint(CENTER - 15, CENTER + 15), 0
    points = [(x, y)]
    while y < SIZE:
        x += random.randint(-25, 25)
        y += random.randint(15, 35)
        x = max(lo, min(hi, x))
        points.append((x, y))
        if random.random() < 0.35 and len(points) > 2:
            bx, by = points[-2]
            ex = max(lo, min(hi, bx + random.randint(-30, 30)))
            ey = by + random.randint(20, 60)
            draw.line([(bx, by), (ex, ey)], fill=(25, 25, 25), width=2)
    draw.line(points, fill=(15, 15, 15), width=4)
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    img.save(path)


def make_rust(path, color):
    img = _base_wall(color)
    draw = ImageDraw.Draw(img, "RGBA")
    for _ in range(6):
        r = random.randint(20, 35)
        jitter = BLOB_EXTENT - r
        cx = CENTER + random.randint(-jitter, jitter)
        cy = CENTER + random.randint(-jitter, jitter)
        for i in range(r, 0, -4):
            alpha = int(140 * (1 - i / r))
            draw.ellipse([cx - i, cy - i, cx + i, cy + i],
                         fill=(120 + random.randint(-15, 15), 60, 20, alpha))
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    img.save(path)


def make_leak(path, color):
    img = _base_wall(color)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width = random.randint(50, 70)
    jitter = LEAK_EXTENT - width // 2
    cx = CENTER + random.randint(-jitter, jitter)
    top = random.randint(0, SIZE // 4)
    bottom = SIZE
    draw.polygon(
        [(cx - width // 2, top), (cx + width // 2, top),
         (cx + width // 3, bottom), (cx - width // 3, bottom)],
        fill=(30, 40, 60, 110),
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(1.5))
    img.save(path)


if __name__ == "__main__":
    random.seed(7)
    make_clean(os.path.join(OUT_DIR, "clean_wall_1.png"), (200, 198, 190))
    make_clean(os.path.join(OUT_DIR, "clean_wall_2.png"), (210, 205, 195))
    make_clean(os.path.join(OUT_DIR, "clean_wall_3.png"), (195, 192, 185))
    make_crack(os.path.join(OUT_DIR, "crack_wall_1.png"), (205, 200, 190))
    make_crack(os.path.join(OUT_DIR, "crack_wall_2.png"), (198, 195, 188))
    make_rust(os.path.join(OUT_DIR, "rust_wall_1.png"), (180, 180, 185))
    make_leak(os.path.join(OUT_DIR, "leak_wall_1.png"), (215, 212, 205))
    print("Wrote textures to", OUT_DIR)
