"""Runs experiments/evaluate.py as many small parallel subprocesses (one per
seed x scenario) and concatenates the parts into one comparison.csv.

Each (seed, scenario) job is a fresh interpreter -- the same isolation
run_full_sweep.sh uses to dodge pybullet's renderer resource build-up -- and
the jobs run N at a time, which is what makes the 31-wall yard (about 3x the
steps per mission of the 9-wall one) tractable.

Usage (from the repo root; env vars select the yard / detector / memory):
  UWTIG_YARD=large UWTIG_MEMORY=inmem MBDD_WEIGHTS=best.pt \
  python experiments/run_parallel_sweep.py --subdir large --budget 50 --seeds 0 1 2 3 4 --jobs 12
"""
import argparse
import csv
import itertools
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS = ["static", "uncertain", "growing", "multi_defect"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subdir", required=True, help="results/<subdir>/ output folder")
    ap.add_argument("--budget", type=int, required=True)
    ap.add_argument("--missions", type=int, default=3)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--scenarios", nargs="+", default=SCENARIOS)
    ap.add_argument("--planners", nargs="+", default=None)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--retries", type=int, default=3)
    args = ap.parse_args()

    out_dir = os.path.join(ROOT, "results", args.subdir)
    os.makedirs(out_dir, exist_ok=True)
    env = dict(os.environ, UWTIG_RESULTS_SUBDIR=args.subdir, PYTHONPATH=ROOT)
    todo = list(itertools.product(args.seeds, args.scenarios))
    running, attempts, done, failed = {}, {}, [], []
    t0 = time.time()
    while todo or running:
        while todo and len(running) < args.jobs:
            seed, scen = todo.pop(0)
            part = os.path.join(out_dir, f"part_seed{seed}_{scen}.csv")
            if os.path.exists(part):
                done.append(part)
                continue
            cmd = [sys.executable, os.path.join(ROOT, "experiments", "evaluate.py"), "--seed", str(seed),
                   "--scenarios", scen, "--budget", str(args.budget), "--missions", str(args.missions), "--out", part]
            if args.planners:
                cmd += ["--planners", *args.planners]
            log = open(os.path.join(out_dir, f"log_seed{seed}_{scen}.txt"), "a")
            running[(seed, scen)] = (subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT), part)
        time.sleep(5)
        for key, (proc, part) in list(running.items()):
            rc = proc.poll()
            if rc is None:
                continue
            del running[key]
            if rc == 0 and os.path.exists(part):
                done.append(part)
                print(f"[{time.time() - t0:6.0f}s] done {key} ({len(done)} parts)", flush=True)
            else:
                attempts[key] = attempts.get(key, 0) + 1
                if attempts[key] < args.retries:
                    todo.append(key)
                    print(f"retry {key} (exit {rc})", flush=True)
                else:
                    failed.append(key)
                    print(f"FAILED {key}", flush=True)

    rows, header = [], None
    for part in sorted(done):
        with open(part, newline="") as f:
            rd = csv.DictReader(f)
            header = header or rd.fieldnames
            rows.extend(rd)
    with open(os.path.join(out_dir, "comparison.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    print(f"merged {len(done)} parts / {len(rows)} rows -> {out_dir}/comparison.csv; failed: {failed}")


if __name__ == "__main__":
    main()
