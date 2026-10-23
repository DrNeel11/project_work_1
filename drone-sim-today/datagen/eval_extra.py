"""Compares detector weights on three test sets, writing results/detector_extra.json.

  mbdd   : the MBDD2025 test split (same 1,448 images used since the first result)
  dacl   : dacl10k 'validation' split mapped to our classes (held out of training)
  crack  : image-level crack presence on the Ozgenel concrete-crack set
           (cracked vs. uncracked 227x227 crops, never trained on) -- the role
           SDNET2018's cracked/uncracked folders would have played

Usage: venv_gpu python -m datagen.eval_extra NAME=weights.pt [NAME=weights.pt ...]
"""
import glob
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRACK_DIR = os.path.join(ROOT, "datasets", "concrete_crack")


def box_metrics(model, yaml, imgsz=640):
    r = model.val(data=yaml, split="test", imgsz=imgsz, verbose=False, plots=False, batch=16)
    return {"map50": float(r.box.map50), "map50_95": float(r.box.map), "p": float(r.box.mp), "r": float(r.box.mr),
            "per_class_ap50": {model.names[int(c)]: float(a) for c, a in zip(r.box.ap_class_index, r.box.ap50)}}


def crack_presence(model, n=400, conf=0.25, seed=0):
    import numpy as np
    from PIL import Image
    files = sorted(glob.glob(os.path.join(CRACK_DIR, "**", "*.*"), recursive=True))
    files = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    pos = [f for f in files if "positive" in f.lower()]
    neg = [f for f in files if "negative" in f.lower() or "uncracked" in f.lower()]
    if not pos or not neg:
        return {"error": f"could not split {len(files)} files into cracked/uncracked"}
    rng = random.Random(seed)
    pos, neg = rng.sample(pos, min(n, len(pos))), rng.sample(neg, min(n, len(neg)))
    crack_id = [i for i, nm in model.names.items() if nm == "crack"][0]

    def hit(paths):
        out = 0
        for i in range(0, len(paths), 32):
            for r in model.predict(paths[i:i + 32], imgsz=640, conf=conf, verbose=False):
                out += int(any(int(c) == crack_id for c in r.boxes.cls.tolist()))
        return out
    tp, fp = hit(pos), hit(neg)
    return {"cracked_images": len(pos), "uncracked_images": len(neg), "recall": tp / len(pos), "false_alarm_rate": fp / len(neg),
            "precision": tp / max(1, tp + fp)}


def main(specs):
    from ultralytics import YOLO
    res = {}
    for spec in specs:
        name, path = spec.split("=", 1)
        m = YOLO(path)
        res[name] = {"mbdd": box_metrics(m, os.path.join(ROOT, "datasets", "mbdd_yolo", "data.yaml")),
                     "dacl": box_metrics(m, os.path.join(ROOT, "datasets", "dacl_eval", "data.yaml")),
                     "crack_presence": crack_presence(m)}
        print(name, json.dumps(res[name], indent=1))
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    out = os.path.join(ROOT, "results", "detector_extra.json")
    json.dump(res, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1:])
