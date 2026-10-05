"""Chooses evaluate.py's report-confirmation rule (CONFIRM_MIN_VIEWS,
CONFIRM_MIN_CONF) on DEV seeds only, from mission logs dumped by
`evaluate.py --dump-logs`. The objective is report-level F1 averaged over ALL
planners equally -- not the novel planner's F1 -- so the rule is not tuned in
UW-TIG's favour. Prints the full grid so the choice is auditable.

Usage: venv python -m experiments.tune_report_rule results/dev_logs_seed*.pkl
"""
import collections
import glob
import pickle
import sys

import numpy as np

sys.path.insert(0, ".")
from experiments import evaluate  # noqa: E402
from experiments.scenarios import SCENARIO_REGISTRY  # noqa: E402

VIEW_GRID = [1, 2, 3]
CONF_GRID = [0.35, 0.45, 0.5, 0.55, 0.6, 0.7, 1.01]  # 1.01 = single looks never suffice


def main(paths):
    runs = []
    for path in paths:
        with open(path, "rb") as f:
            runs.extend(pickle.load(f))
    print(f"{len(runs)} dev runs loaded from {len(paths)} file(s)\n")

    results = []
    for min_views in VIEW_GRID:
        for min_conf in CONF_GRID:
            evaluate.CONFIRM_MIN_VIEWS, evaluate.CONFIRM_MIN_CONF = min_views, min_conf
            per_planner = collections.defaultdict(list)
            for planner, scen_name, seed, logs in runs:
                row = evaluate.summarize_run(planner, scen_name, seed, logs, SCENARIO_REGISTRY[scen_name](seed=seed))
                per_planner[planner].append((row["precision_confirmed"], row["recall_confirmed"], row["f1_confirmed"]))
            summary = {p: tuple(np.nanmean([v[i] for v in vals]) for i in range(3)) for p, vals in per_planner.items()}
            mean_f1 = float(np.mean([s[2] for s in summary.values()]))
            results.append((mean_f1, min_views, min_conf, summary))

    planners = sorted(results[0][3])
    print(f"{'views':>5s} {'conf':>5s} {'meanF1':>7s}  " + "  ".join(f"{p:>22s}" for p in planners))
    for mean_f1, v, c, summary in results:
        cells = "  ".join(f"P{summary[p][0]:.2f} R{summary[p][1]:.2f} F{summary[p][2]:.2f}".rjust(22) for p in planners)
        print(f"{v:5d} {c:5.2f} {mean_f1:7.3f}  {cells}")
    best = max(results, key=lambda r: r[0])
    print(f"\nchosen (max planner-averaged F1 on dev): CONFIRM_MIN_VIEWS={best[1]} CONFIRM_MIN_CONF={best[2]}")


if __name__ == "__main__":
    args = sys.argv[1:] or sorted(glob.glob("results/dev_logs_seed*.pkl"))
    main(args)
