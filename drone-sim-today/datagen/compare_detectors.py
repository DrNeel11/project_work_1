"""Fair detector comparison: YOLOv8n/s/m trained with identical settings on the same fixed subset of MBDD2025,
then evaluated on the full 1,448-image test split.  Usage: python datagen/compare_detectors.py [n s m]"""
import json, os, random, sys
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DS = os.path.join(ROOT, "datasets", "mbdd_yolo")
OUT = os.path.join(ROOT, "results", "detector_compare")
os.makedirs(OUT, exist_ok=True)
N_TRAIN, N_VAL, EPOCHS, IMGSZ, BATCH, SEED = 4000, 600, 30, 640, 8, 0


def subset(split, n):
    d = os.path.join(DS, "images", split)
    files = sorted(os.listdir(d))
    random.Random(SEED).shuffle(files)
    path = os.path.join(OUT, f"{split}_subset.txt")
    open(path, "w").write("\n".join(os.path.join(d, f) for f in files[:n]))
    return path


def main():
    yaml = os.path.join(OUT, "data_subset.yaml")
    open(yaml, "w").write(f"path: {DS}\ntrain: {subset('train', N_TRAIN)}\nval: {subset('val', N_VAL)}\ntest: images/test\n"
                          "names: ['crack', 'leakage', 'abscission', 'corrosion', 'bulge']\n")
    res_file = os.path.join(OUT, "results.json")
    res = json.load(open(res_file)) if os.path.exists(res_file) else {}
    for size in (sys.argv[1:] or ["n", "s", "m"]):
        name = f"yolov8{size}"
        m = YOLO(f"{name}.pt")
        m.train(data=yaml, epochs=EPOCHS, imgsz=IMGSZ, batch=BATCH, seed=SEED, deterministic=True, workers=0,
                project=OUT, name=name, exist_ok=True, patience=0, plots=False, verbose=False)
        best = YOLO(os.path.join(OUT, name, "weights", "best.pt"))
        r = best.val(data=os.path.join(DS, "data.yaml"), split="test", imgsz=IMGSZ, batch=16, plots=False)
        res[name] = dict(map50=float(r.box.map50), map5095=float(r.box.map), precision=float(r.box.mp), recall=float(r.box.mr),
                         params_m=sum(p.numel() for p in best.model.parameters()) / 1e6)
        json.dump(res, open(res_file, "w"), indent=1)
        print(name, res[name], flush=True)



if __name__ == "__main__":
    main()
