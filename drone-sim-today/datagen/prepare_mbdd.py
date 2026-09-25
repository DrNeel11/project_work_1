"""Turns the extracted MBDD2025 archive (datasets/MBDD2025/{JPEGImages,Labels}/,
flat, no pre-made split -- confirmed by inspecting the archive) into an
ultralytics-ready layout: datasets/mbdd_yolo/{images,labels}/{train,val,test}/,
hardlinked (not copied) from the original files to avoid duplicating ~2.5GB,
plus data.yaml.

Label files are already YOLO-format (class_id cx cy w h, normalized); the
class-id order below was recovered empirically by cross-referencing each
Annotations/*.xml's <name> tags against the matching Labels/*.txt row order
(several dozen files checked, fully consistent): 0=crack, 1=leakage,
2=abscission, 3=corrosion, 4=bulge.
"""
import argparse
import os
import random

CLASS_NAMES = ["crack", "leakage", "abscission", "corrosion", "bulge"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_IMAGES = os.path.join(ROOT, "datasets", "MBDD2025", "JPEGImages")
SRC_LABELS = os.path.join(ROOT, "datasets", "MBDD2025", "Labels")
DST_ROOT = os.path.join(ROOT, "datasets", "mbdd_yolo")

SPLIT_FRACS = {"train": 0.70, "val": 0.20, "test": 0.10}


def _link(src, dst):
    if os.path.exists(dst):
        return
    try:
        os.link(src, dst)
    except OSError:
        import shutil
        shutil.copy2(src, dst)


def build(seed=0, limit=None):
    basenames = sorted(f[:-4] for f in os.listdir(SRC_IMAGES) if f.endswith(".jpg"))
    basenames = [b for b in basenames if os.path.exists(os.path.join(SRC_LABELS, b + ".txt"))]
    print(f"found {len(basenames)} image/label pairs")
    if limit:
        basenames = basenames[:limit]

    rng = random.Random(seed)
    rng.shuffle(basenames)
    n = len(basenames)
    n_train = int(n * SPLIT_FRACS["train"])
    n_val = int(n * SPLIT_FRACS["val"])
    splits = {
        "train": basenames[:n_train],
        "val": basenames[n_train:n_train + n_val],
        "test": basenames[n_train + n_val:],
    }

    for split, names in splits.items():
        img_dir = os.path.join(DST_ROOT, "images", split)
        lbl_dir = os.path.join(DST_ROOT, "labels", split)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)
        for b in names:
            _link(os.path.join(SRC_IMAGES, b + ".jpg"), os.path.join(img_dir, b + ".jpg"))
            _link(os.path.join(SRC_LABELS, b + ".txt"), os.path.join(lbl_dir, b + ".txt"))
        print(f"  {split}: {len(names)} images -> {img_dir}")

    yaml_path = os.path.join(DST_ROOT, "data.yaml")
    with open(yaml_path, "w") as f:
        f.write(f"path: {DST_ROOT}\n")
        f.write("train: images/train\nval: images/val\ntest: images/test\n")
        f.write(f"names: {CLASS_NAMES}\n")
    print("wrote", yaml_path)
    return yaml_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None, help="cap total images, for a fast smoke test")
    args = ap.parse_args()
    build(seed=args.seed, limit=args.limit)
