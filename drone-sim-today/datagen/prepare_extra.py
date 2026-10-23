"""Builds datasets/mbdd_plus: the MBDD2025 split (train/val/test unchanged, so the
MBDD test set stays comparable with earlier results) enriched with two further
public, openly licensed (CC-BY-4.0) defect datasets, mapped into our five classes.

  dacl10k (Flotzinger et al., WACV 2024; 8,922 labelled real bridge-inspection
      photographs, Voxel51/dacl10k on Hugging Face) -- bounding boxes derived by
      the dataset's own detection layer:
        Crack, ACrack (alligator crack)            -> crack
        Wetspot, Efflorescence                     -> leakage
        Spalling, Rockpocket                       -> abscission
        Rust, ExposedRebars                        -> corrosion
      (no bulge source; other dacl10k classes are ignored.) The dacl10k 'train'
      split feeds training (92%) and validation (8%); its 'validation' split is
      kept untouched as a held-out cross-dataset test set (datasets/dacl_eval).
  Roboflow-100 "corrosion-bi3q3" (CC-BY-4.0): corrosion -> corrosion, crack -> crack
      (its "Slippage" class is dropped). train+valid feed training.

SDNET2018 (the dataset the group first planned to add) is bot-gated on every
mirror we could reach, so these openly downloadable datasets replace it.

A concrete-crack classification set (Ozgenel, 40k 227x227 crops, CC-BY-4.0,
mohammadnajeeb/concrete_crack_images) is *not* trained on: it is a held-out,
image-level crack-presence check (datagen/eval_extra.py), the role SDNET2018's
cracked/uncracked folders would have played.

Usage: venv python datagen/prepare_extra.py
"""
import json
import os
import random
import shutil

from datagen.prepare_mbdd import CLASS_NAMES, DST_ROOT as MBDD_ROOT, _link

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DACL = os.path.join(ROOT, "datasets", "dacl10k")
CORR = os.path.join(ROOT, "datasets", "corrosion_rf")
OUT = os.path.join(ROOT, "datasets", "mbdd_plus")
EVAL_OUT = os.path.join(ROOT, "datasets", "dacl_eval")

DACL_MAP = {"Crack": "crack", "ACrack": "crack", "Wetspot": "leakage", "Efflorescence": "leakage",
            "Spalling": "abscission", "Rockpocket": "abscission", "Rust": "corrosion",
            "ExposedRebars": "corrosion"}
CORR_MAP = {"corrosion": "corrosion", "crack": "crack"}
MIN_BOX = 0.01  # drop boxes thinner than 1% of the image side


def cid(name):
    return CLASS_NAMES.index(name)


def clip_box(x, y, w, h):
    x0, y0 = max(0.0, x), max(0.0, y)
    x1, y1 = min(1.0, x + w), min(1.0, y + h)
    return (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0


def dacl_items():
    samples = json.load(open(os.path.join(DACL, "samples.json"), encoding="utf-8"))["samples"]
    out = {"train": [], "validation": []}
    for s in samples:
        tag = s["tags"][0] if s["tags"] else None
        od = s.get("od_ground_truth")
        if tag not in out or not od:
            continue
        lines = []
        for d in od["detections"]:
            cls = DACL_MAP.get(d["label"])
            if cls is None:
                continue
            cx, cy, w, h = clip_box(*d["bounding_box"])
            if w < MIN_BOX or h < MIN_BOX:
                continue
            lines.append(f"{cid(cls)} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
        src = os.path.join(DACL, s["filepath"])
        if lines and os.path.exists(src):
            out[tag].append((src, s["name"], lines))
    return out


def write(split_root, split, name, src, lines):
    idir = os.path.join(split_root, "images", split)
    ldir = os.path.join(split_root, "labels", split)
    os.makedirs(idir, exist_ok=True)
    os.makedirs(ldir, exist_ok=True)
    _link(src, os.path.join(idir, name + ".jpg"))
    with open(os.path.join(ldir, name + ".txt"), "w") as f:
        f.write("\n".join(lines) + "\n")


def corrosion_items():
    items = []
    for split in ("train", "valid"):
        idir = os.path.join(CORR, split, "images")
        ldir = os.path.join(CORR, split, "labels")
        if not os.path.isdir(idir):
            continue
        names = [l.strip("- \n") for l in open(os.path.join(CORR, "data.yaml")).read().split("nc:")[0].split("\n")[1:] if l.strip()]
        for fn in sorted(os.listdir(idir)):
            lp = os.path.join(ldir, os.path.splitext(fn)[0] + ".txt")
            if not os.path.exists(lp):
                continue
            lines = []
            for ln in open(lp).read().split("\n"):
                p = ln.split()
                if len(p) != 5:
                    continue
                cls = CORR_MAP.get(names[int(p[0])])
                if cls:
                    lines.append(f"{cid(cls)} {p[1]} {p[2]} {p[3]} {p[4]}")
            if lines:
                items.append((os.path.join(idir, fn), "rf_" + os.path.splitext(fn)[0][:60], lines))
    return items


def main(seed=0):
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    # MBDD splits, unchanged
    for split in ("train", "val", "test"):
        for kind, ext in (("images", ".jpg"), ("labels", ".txt")):
            src_dir = os.path.join(MBDD_ROOT, kind, split)
            dst_dir = os.path.join(OUT, kind, split)
            os.makedirs(dst_dir, exist_ok=True)
            for fn in os.listdir(src_dir):
                _link(os.path.join(src_dir, fn), os.path.join(dst_dir, fn))
    n_mbdd = {s: len(os.listdir(os.path.join(OUT, "images", s))) for s in ("train", "val", "test")}

    rng = random.Random(seed)
    d = dacl_items()
    rng.shuffle(d["train"])
    n_val = int(0.08 * len(d["train"]))
    counts = {"dacl_train": 0, "dacl_val": 0, "corrosion": 0}
    for i, (src, name, lines) in enumerate(d["train"]):
        split = "val" if i < n_val else "train"
        write(OUT, split, "dacl_" + name, src, lines)
        counts["dacl_val" if split == "val" else "dacl_train"] += 1
    for src, name, lines in corrosion_items():
        write(OUT, "train", name, src, lines)
        counts["corrosion"] += 1
    # held-out cross-dataset test: dacl10k 'validation'
    if os.path.isdir(EVAL_OUT):
        shutil.rmtree(EVAL_OUT)
    for src, name, lines in d["validation"]:
        write(EVAL_OUT, "test", "dacl_" + name, src, lines)

    for root, extra in ((OUT, "val: images/val\ntest: images/test\n"), (EVAL_OUT, "val: images/test\ntest: images/test\n")):
        with open(os.path.join(root, "data.yaml"), "w") as f:
            f.write(f"path: {root}\ntrain: images/train\n" if root == OUT else f"path: {root}\ntrain: images/test\n")
            f.write(extra)
            f.write(f"names: {CLASS_NAMES}\n")
    print("MBDD", n_mbdd, "added", counts, "dacl held-out test", len(d["validation"]))


if __name__ == "__main__":
    main()
