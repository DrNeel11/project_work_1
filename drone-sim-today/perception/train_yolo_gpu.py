"""GPU retrain: same MBDD2025 data as the original CPU run
(perception/train_yolo.py) but at a realistic budget once real compute is
available -- higher resolution (640 vs the CPU run's 320px, which mattered
most for thin/low-contrast defects like cracks: recall 0.45 -> 0.75), a
larger model (yolov8s vs yolov8n), more epochs (100 vs 30), and bulge-class
oversampling applied via datagen/oversample_bulge.py beforehand (bulge
recall 0.58 -> 0.96). Run on a CUDA machine (device=0) -- this project's GPU
run used an NVIDIA L4 on a rented Linux VM, not the CPU-only dev machine
perception/train_yolo.py targets. Full before/after numbers in RESULTS.md.
"""
import argparse
import os

from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_YAML = os.path.join(ROOT, "datasets", "mbdd_yolo", "data.yaml")
WEIGHTS_DIR = os.path.join(ROOT, "weights")
os.makedirs(WEIGHTS_DIR, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--model", default="yolov8s.pt")
    ap.add_argument("--name", default="mbdd_yolov8s_gpu")
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cache", default=False, help="'ram' to cache decoded images (needs ~15GB RAM at 640px)")
    args = ap.parse_args()

    model = YOLO(args.model)
    model.train(
        data=DATA_YAML, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch,
        device=0, project=WEIGHTS_DIR, name=args.name, exist_ok=True, patience=args.patience,
        workers=args.workers, cache=args.cache,
    )
    best = os.path.join(WEIGHTS_DIR, args.name, "weights", "best.pt")
    print("best weights ->", best)

    metrics = YOLO(best).val(data=DATA_YAML, split="test", device=0)
    print("TEST SET mAP50:", metrics.box.map50, "mAP50-95:", metrics.box.map)
    print("TEST SET per-class P:", metrics.box.p)
    print("TEST SET per-class R:", metrics.box.r)


if __name__ == "__main__":
    main()
