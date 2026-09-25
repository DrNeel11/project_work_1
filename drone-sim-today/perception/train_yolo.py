"""Trains YOLOv8n (detection) on MBDD2025's real bbox-annotated UAV photos
(datagen/prepare_mbdd.py produces the data.yaml this points at). CPU-budget
epoch/imgsz defaults are deliberately modest -- see RESULTS.md for the
stated caveat about training-budget limits.
"""
import argparse
import os

from ultralytics import YOLO

DEFAULT_DATA_YAML = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "datasets", "mbdd_yolo", "data.yaml")
WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "weights")
os.makedirs(WEIGHTS_DIR, exist_ok=True)


def train(data_yaml=DEFAULT_DATA_YAML, epochs=40, imgsz=320, batch=8, base="yolov8n.pt"):
    model = YOLO(base)
    results = model.train(
        data=data_yaml, epochs=epochs, imgsz=imgsz, batch=batch, device="cpu",
        project=WEIGHTS_DIR, name="mbdd_yolov8n", exist_ok=True, patience=15,
    )
    best = os.path.join(WEIGHTS_DIR, "mbdd_yolov8n", "weights", "best.pt")
    print("best weights ->", best)
    return best, results


def validate(weights, data_yaml=DEFAULT_DATA_YAML, split="test"):
    model = YOLO(weights)
    metrics = model.val(data=data_yaml, split=split, device="cpu")
    print("mAP50:", metrics.box.map50, "mAP50-95:", metrics.box.map)
    print("per-class P/R:", metrics.box.p, metrics.box.r)
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DEFAULT_DATA_YAML)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--val-only", default=None, help="path to weights to just validate, skip training")
    args = ap.parse_args()

    if args.val_only:
        validate(args.val_only, args.data)
    else:
        best, _ = train(args.data, epochs=args.epochs, imgsz=args.imgsz, batch=args.batch)
        validate(best, args.data)
