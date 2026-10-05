"""Wraps the trained YOLOv8n (perception/train_yolo.py) behind the
detect(bgr) -> [{bbox, label, confidence, uncertainty}] interface used by
experiments/mission.py and demo_uwtig_flight.py.

Uncertainty is a test-time-augmentation (TTA) ensemble variance, NOT true
MC-Dropout -- stock YOLOv8 has no dropout retained at inference. K
photometric-only variants (brightness/contrast/noise/blur -- nothing that
moves box geometry, so no re-alignment is needed) are run through the same
model; for each detection in the original frame, its confidence's standard
deviation across the ensemble (0 counted for variants where no matching box
is found) is reported as `uncertainty`. This is the documented substitute
described in RESULTS.md.
"""
import os

import cv2
import numpy as np
from ultralytics import YOLO

from datagen.prepare_mbdd import CLASS_NAMES

DEFAULT_WEIGHTS = os.environ.get(
    "MBDD_WEIGHTS",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "weights", "mbdd_yolov8s_gpu", "weights", "best.pt"),
)
CONF_THRESH = 0.25
IOU_MATCH_THRESH = 0.3

_model_cache = {}


def _get_model(weights=DEFAULT_WEIGHTS):
    if weights not in _model_cache:
        _model_cache[weights] = YOLO(weights)
    return _model_cache[weights]


def _augment(bgr, rng):
    bright = cv2.convertScaleAbs(bgr, alpha=rng.uniform(0.8, 1.2), beta=rng.uniform(-20, 20))
    noisy = np.clip(bgr.astype(np.float32) + rng.normal(0, 10, bgr.shape), 0, 255).astype(np.uint8)
    blurred = cv2.GaussianBlur(bgr, (3, 3), 0)
    bright_blur = cv2.convertScaleAbs(cv2.GaussianBlur(bgr, (3, 3), 0),
                                       alpha=rng.uniform(0.85, 1.15), beta=rng.uniform(-15, 15))
    return [bright, noisy, blurred, bright_blur]


def _iou_xyxy(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def square_pixels(bgr):
    """The drone camera (gym-pybullet-drones BaseAviary, mirrored in
    geometry.drone_camera_matrices) renders a 60 deg x 60 deg field of view
    into a non-square image (e.g. 320x240), so every frame is stretched
    horizontally by width/height (1.33x). The detector was trained on real,
    undistorted photos -- resample to square pixels (W x W) before inference.
    Returns (frame, y_scale) where y_scale maps detected y back to the
    original frame's coordinates, which geometry.py's localization expects."""
    h, w = bgr.shape[:2]
    if h == w:
        return bgr, 1.0
    return cv2.resize(bgr, (w, w), interpolation=cv2.INTER_LINEAR), h / w


def detect_with_uncertainty(bgr, weights=DEFAULT_WEIGHTS, conf_thresh=CONF_THRESH, seed=None, imgsz=320):
    model = _get_model(weights)
    rng = np.random.RandomState(seed) if seed is not None else np.random

    frame, y_scale = square_pixels(bgr)
    variants = [frame] + _augment(frame, rng)
    preds = [model.predict(v, conf=0.1, verbose=False, imgsz=imgsz)[0] for v in variants]

    canonical = preds[0]
    results = []
    for box in canonical.boxes:
        conf = float(box.conf.item())
        if conf < conf_thresh:
            continue
        cls_id = int(box.cls.item())
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        bbox = (int(round(x1)), int(round(y1 * y_scale)), int(round(x2 - x1)), int(round((y2 - y1) * y_scale)))

        confs = [conf]
        for pred in preds[1:]:
            best_iou, best_conf = 0.0, 0.0
            for b2 in pred.boxes:
                if int(b2.cls.item()) != cls_id:
                    continue
                iou = _iou_xyxy((x1, y1, x2, y2), b2.xyxy[0].tolist())
                if iou > best_iou:
                    best_iou, best_conf = iou, float(b2.conf.item())
            confs.append(best_conf if best_iou > IOU_MATCH_THRESH else 0.0)

        results.append({
            "bbox": bbox, "label": CLASS_NAMES[cls_id], "confidence": conf,
            "uncertainty": float(np.std(confs)),
        })
    return results


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        img = cv2.imread(path)
        for d in detect_with_uncertainty(img):
            print(d)
    else:
        print("usage: python -m perception.ml_detector <image_path>")
