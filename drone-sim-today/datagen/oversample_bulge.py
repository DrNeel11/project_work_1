"""Oversamples bulge-containing training images (class id 4, the rarest
class by a wide margin -- 2018 instances vs abscission's 22702) by
duplicating them 3x into the train split, as symlinked copies with a
distinguishing filename suffix. Run once against datasets/mbdd_yolo/
(after datagen/prepare_mbdd.py) and before training -- see
perception/train_yolo_gpu.py, whose GPU retrain used this to lift bulge
recall from 0.58 to 0.96 (RESULTS.md). Labels are duplicated too (same
content, different name) so ultralytics treats each copy as a distinct
training example, increasing bulge's effective sampling frequency by ~4x
total (1 original + 3 copies) without touching val/test.

Uses os.symlink, which needs a POSIX filesystem (or Windows Developer Mode
enabled) -- run this on the training machine (this project's GPU runs were
done on a Linux VM), not necessarily the same machine prepare_mbdd.py ran
datasets/mbdd_yolo/ on.
"""
import os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "datasets", "mbdd_yolo")
IMG_DIR = os.path.join(ROOT, "images", "train")
LBL_DIR = os.path.join(ROOT, "labels", "train")
N_COPIES = 3
BULGE_CLASS = "4"


def _link(src, dst):
    """Symlink where allowed; on Windows without Developer Mode fall back to an
    NTFS hard link (no admin needed, still no extra disk space)."""
    try:
        os.symlink(os.path.abspath(src), dst)
    except OSError:
        os.link(src, dst)


def main():
    bulge_images = []
    for fname in os.listdir(LBL_DIR):
        if not fname.endswith(".txt"):
            continue
        with open(os.path.join(LBL_DIR, fname)) as f:
            classes = {line.split()[0] for line in f if line.strip()}
        if BULGE_CLASS in classes:
            bulge_images.append(fname[:-4])

    print(f"found {len(bulge_images)} train images containing bulge")
    made = 0
    for base in bulge_images:
        img_src = os.path.join(IMG_DIR, base + ".jpg")
        lbl_src = os.path.join(LBL_DIR, base + ".txt")
        if not os.path.exists(img_src):
            continue
        for i in range(1, N_COPIES + 1):
            img_dst = os.path.join(IMG_DIR, f"{base}_bulgedup{i}.jpg")
            lbl_dst = os.path.join(LBL_DIR, f"{base}_bulgedup{i}.txt")
            if os.path.exists(img_dst):
                continue
            _link(img_src, img_dst)
            _link(lbl_src, lbl_dst)
            made += 1
    print(f"created {made} duplicate image+label pairs "
          f"(~{len(bulge_images) * N_COPIES} bulge instance exposures added)")


if __name__ == "__main__":
    main()
