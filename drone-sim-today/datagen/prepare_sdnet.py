"""Merges a balanced subsample of SDNET2018 (Maguire, Dorafshan & Thomas,
2018; CC-BY-4.0; https://doi.org/10.15142/T3TD19) into the existing
MBDD2025 YOLO split (datagen/prepare_mbdd.py) -- the public benchmark
Inam et al. (2023), one of the cited base papers, combines with their own
field data for crack detection. This repeats that combination: a real,
differently-framed (perpendicular closeup on bridge decks/walls/pavements,
not oblique UAV) but genuinely public, literature-cited data source
enriching the "crack" class alongside MBDD2025.

SDNET2018 is whole-image classification (cracked/uncracked 256x256 crops),
not bounding boxes: a cracked image becomes a single full-image weak box
for the "crack" class; an uncracked image becomes a pure background
(empty label) negative. Folder layout (confirmed against the dataset's own
documentation): D/CD, D/UD (bridge decks), W/CW, W/UW (walls), P/CP, P/UP
(pavements), C=cracked, U=uncracked.

Usage: venv python datagen/prepare_sdnet.py [--n-cracked 1500] [--n-uncracked 1500]
Expects datasets/SDNET2018.zip (manually downloaded -- see README.md) or an
already-extracted datasets/SDNET2018/.
"""
import argparse
import os
import random
import zipfile

from datagen.prepare_mbdd import CLASS_NAMES, DST_ROOT, SPLIT_FRACS, _link

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_PATH = os.path.join(ROOT, "datasets", "SDNET2018.zip")
SDNET_ROOT = os.path.join(ROOT, "datasets", "SDNET2018")

CRACKED_DIRS = ["D/CD", "W/CW", "P/CP"]
UNCRACKED_DIRS = ["D/UD", "W/UW", "P/UP"]
CRACK_CLASS_ID = CLASS_NAMES.index("crack")
CRACK_WEAK_LABEL = f"{CRACK_CLASS_ID} 0.5 0.5 0.98 0.98\n"


def ensure_extracted():
    if os.path.isdir(SDNET_ROOT) and any(os.scandir(SDNET_ROOT)):
        return
    if not os.path.exists(ZIP_PATH):
        raise FileNotFoundError(
            f"{ZIP_PATH} not found. Download SDNET2018.zip from "
            "https://digitalcommons.usu.edu/all_datasets/48/ (CC-BY-4.0, ~504MB) "
            "and place it there -- it's behind a bot-check that blocks scripted downloads."
        )
    print("extracting", ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extractall(SDNET_ROOT)


def _find_dir(leaf_name):
    """SDNET2018 zips in the wild sometimes nest an extra top-level folder
    (e.g. SDNET2018/SDNET2018/D/CD/) -- search for the leaf dir by name
    rather than assuming a fixed depth."""
    for root, dirs, _ in os.walk(SDNET_ROOT):
        if os.path.basename(root) == leaf_name:
            return root
    return None


def _collect(subdirs):
    files = []
    for sub in subdirs:
        d = os.path.join(SDNET_ROOT, sub)
        if not os.path.isdir(d):
            d = _find_dir(sub.split("/")[-1])
        if not d:
            print(f"  warning: couldn't find {sub}, skipping")
            continue
        files.extend(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".jpg"))
    return files


def build(n_cracked=1500, n_uncracked=1500, seed=1):
    ensure_extracted()
    rng = random.Random(seed)

    cracked = _collect(CRACKED_DIRS)
    uncracked = _collect(UNCRACKED_DIRS)
    print(f"found {len(cracked)} cracked, {len(uncracked)} uncracked SDNET2018 images")
    rng.shuffle(cracked)
    rng.shuffle(uncracked)
    cracked = cracked[:n_cracked]
    uncracked = uncracked[:n_uncracked]

    items = [(p, True) for p in cracked] + [(p, False) for p in uncracked]
    rng.shuffle(items)

    n = len(items)
    n_train = int(n * SPLIT_FRACS["train"])
    n_val = int(n * SPLIT_FRACS["val"])
    splits = {
        "train": items[:n_train],
        "val": items[n_train:n_train + n_val],
        "test": items[n_train + n_val:],
    }

    for split, split_items in splits.items():
        img_dir = os.path.join(DST_ROOT, "images", split)
        lbl_dir = os.path.join(DST_ROOT, "labels", split)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)
        for i, (src_path, is_cracked) in enumerate(split_items):
            name = f"sdnet_{split}_{i}"
            _link(src_path, os.path.join(img_dir, name + ".jpg"))
            label_path = os.path.join(lbl_dir, name + ".txt")
            with open(label_path, "w") as f:
                if is_cracked:
                    f.write(CRACK_WEAK_LABEL)
        print(f"  {split}: +{len(split_items)} SDNET2018 images")

    print("Re-run `python -m perception.train_yolo` to retrain on the combined dataset.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-cracked", type=int, default=1500)
    ap.add_argument("--n-uncracked", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    build(n_cracked=args.n_cracked, n_uncracked=args.n_uncracked, seed=args.seed)
