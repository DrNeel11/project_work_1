"""Random NBV vs Isler-NBV vs UW-TIG (+2 ablations) x 4 scenarios x N seeds,
each a short sequence of missions (so temporal/growth signals have a chance
to matter). Writes results/comparison.csv, prints a summary table, and
saves matplotlib comparison charts to results/.

Usage: venv python -m experiments.evaluate [--seeds N] [--budget N] [--quick]
"""
import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geometry as geo  # noqa: E402
from experiments.mission import run_mission  # noqa: E402
from experiments.scenarios import SCENARIO_REGISTRY  # noqa: E402
from memory.store import MemoryStore  # noqa: E402
from planning.planners import PLANNER_REGISTRY  # noqa: E402
from sim_house import WALL_SEGMENTS  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
WALL_BY_NAME = {w["name"]: w for w in WALL_SEGMENTS}


def _gt_wall_classes(gt):
    return {(wall, info["defect_type"]) for wall, info in gt.items() if info["defect_type"] != "clean"}


def summarize_run(planner_name, scenario_name, seed, mission_logs, scenario):
    tp = fp = fn = 0
    loc_errors = []
    visited_walls_ever = set()
    gt_walls_ever = set()
    revisit_count = {}
    defect_first_last = {}  # defect_id -> (first_uncertainty, last_uncertainty, first_size, last_size, n_obs)
    total_dist = sum(m["total_dist"] for m in mission_logs)
    total_viewpoints = sum(m["n_viewpoints"] for m in mission_logs)
    n_cells_total = len(WALL_SEGMENTS) * 4  # planning.viewpoints.N_CELLS
    final_entropy = mission_logs[-1]["final_mean_entropy"] * n_cells_total

    for m in mission_logs:
        gt_classes = _gt_wall_classes(m["ground_truth"])
        gt_walls_ever |= {w for w, _ in gt_classes}
        wall_hits = set()

        for step in m["steps"]:
            visited_walls_ever.add(step["wall"])
            if step["wall"] in {w for w, _ in gt_classes}:
                revisit_count[step["wall"]] = revisit_count.get(step["wall"], 0) + 1
            for det in step["detections"]:
                is_tp = (step["wall"], det["label"]) in gt_classes
                if is_tp:
                    wall_hits.add((step["wall"], det["label"]))
                    wall = WALL_BY_NAME[step["wall"]]
                    center = scenario._centers.get(step["wall"])
                    if center is not None:
                        gt_xyz = geo.texture_uv_to_world(wall, *center)
                        loc_errors.append(float(np.linalg.norm(np.array(det["world_xyz"]) - gt_xyz)))
                else:
                    fp += 1

                did = det["defect_id"]
                rec = defect_first_last.setdefault(did, [det["uncertainty"], det["uncertainty"],
                                                          det["size_m"], det["size_m"], 0])
                rec[1] = det["uncertainty"]
                rec[3] = det["size_m"]
                rec[4] += 1

        tp += len(wall_hits)
        fn += len(gt_classes - wall_hits)

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision and recall and (precision + recall)) else float("nan")

    reinspect_targets = [w for w in gt_walls_ever if revisit_count.get(w, 0) > 1]
    reinspection_rate = len(reinspect_targets) / len(gt_walls_ever) if gt_walls_ever else float("nan")

    multi_obs = [r for r in defect_first_last.values() if r[4] >= 2]
    uncertainty_reduction = float(np.mean([r[0] - r[1] for r in multi_obs])) if multi_obs else float("nan")
    growth_detected = float(np.mean([r[3] > r[2] for r in multi_obs])) if multi_obs else float("nan")

    return {
        "planner": planner_name, "scenario": scenario_name, "seed": seed,
        "precision": precision, "recall": recall, "f1": f1,
        "mean_localization_error_m": float(np.mean(loc_errors)) if loc_errors else float("nan"),
        "total_flight_dist_m": total_dist, "total_viewpoints": total_viewpoints,
        "coverage_frac": len(visited_walls_ever) / len(WALL_SEGMENTS),
        "reinspection_rate": reinspection_rate,
        "uncertainty_reduction": uncertainty_reduction,
        "growth_detected_frac": growth_detected,
        "info_gain_per_viewpoint": (n_cells_total - final_entropy) / total_viewpoints if total_viewpoints else float("nan"),
    }


def run_sweep(detector, planners, scenarios, seeds, missions_per_scenario, budget):
    rows = []
    with MemoryStore() as mem:
        for scenario_name in scenarios:
            for seed in seeds:
                for planner_name in planners:
                    scen = SCENARIO_REGISTRY[scenario_name](seed=seed)
                    rng = np.random.RandomState(seed)
                    logs = [run_mission(planner_name, scen, mi, detector, mem, rng, budget=budget, seed=seed)
                            for mi in range(1, missions_per_scenario + 1)]
                    rows.append(summarize_run(planner_name, scenario_name, seed, logs, scen))
                    print(f"  done: {planner_name:22s} {scenario_name:12s} seed={seed}")
    return rows


def write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def print_summary_table(rows):
    import collections
    by_planner = collections.defaultdict(list)
    for r in rows:
        by_planner[r["planner"]].append(r)
    cols = ["precision", "recall", "f1", "mean_localization_error_m", "total_flight_dist_m",
            "coverage_frac", "reinspection_rate", "uncertainty_reduction", "growth_detected_frac",
            "info_gain_per_viewpoint"]
    print("\n=== Summary (mean over scenarios x seeds) ===")
    header = f"{'planner':22s}" + "".join(f"{c:>18s}" for c in cols)
    print(header)
    for planner, rs in by_planner.items():
        vals = [np.nanmean([r[c] for r in rs]) for c in cols]
        print(f"{planner:22s}" + "".join(f"{v:18.3f}" for v in vals))


def make_plots(rows, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import collections

    by_planner = collections.defaultdict(list)
    for r in rows:
        by_planner[r["planner"]].append(r)
    planners = list(by_planner.keys())

    metrics = ["f1", "reinspection_rate", "uncertainty_reduction", "growth_detected_frac",
               "total_flight_dist_m", "info_gain_per_viewpoint"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, metric in zip(axes.flat, metrics):
        means = [np.nanmean([r[metric] for r in by_planner[p]]) for p in planners]
        ax.bar(planners, means, color=["#888" if p != "uwtig" else "#2b6cb0" for p in planners])
        ax.set_title(metric)
        ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    path = os.path.join(out_dir, "comparison.png")
    fig.savefig(path, dpi=140)
    print("wrote", path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--budget", type=int, default=16)
    ap.add_argument("--missions", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="1 seed, small budget, for a smoke test")
    args = ap.parse_args()

    if args.quick:
        args.seeds, args.budget, args.missions = 1, 8, 2

    from perception.ml_detector import detect_with_uncertainty as detector

    planners = list(PLANNER_REGISTRY.keys())
    scenarios = list(SCENARIO_REGISTRY.keys())
    seeds = list(range(args.seeds))

    rows = run_sweep(detector, planners, scenarios, seeds, args.missions, args.budget)
    write_csv(rows, os.path.join(RESULTS_DIR, "comparison.csv"))
    print_summary_table(rows)
    make_plots(rows, RESULTS_DIR)
