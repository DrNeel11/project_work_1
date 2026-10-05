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
from planning.viewpoints import n_cells_for_wall  # noqa: E402
from sim_house import WALL_SEGMENTS  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
WALL_BY_NAME = {w["name"]: w for w in WALL_SEGMENTS}


# A defect counts as "confirmed" in the inspection report once it has been
# seen in >= CONFIRM_MIN_VIEWS separate looks (accumulated across missions --
# persistent memory carries the count forward), or once in a single look at
# >= CONFIRM_MIN_CONF. Applied identically to every planner. Chosen on dev
# seeds (experiments/diagnose_detection.py), never on the reported seeds.
CONFIRM_MIN_VIEWS = 3
CONFIRM_MIN_CONF = 0.45


def _gt_sets(gt):
    """(primary, present): primary = the defect the scenario deliberately
    placed on each wall (what recall is measured against); present = every
    class actually labeled inside that wall's real MBDD2025 photo crop. A
    report of a present-but-not-primary class is a correct detection of a
    real labeled defect, so it is ignored -- neither TP nor FP (COCO-style
    ignore semantics) -- rather than wrongly scored as a false positive."""
    primary = {(w, info["defect_type"]) for w, info in gt.items() if info["defect_type"] != "clean"}
    present = set(primary)
    for w, info in gt.items():
        present |= {(w, c) for c in info.get("present_classes", ())}
    return primary, present


def _prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    if np.isnan(precision) or np.isnan(recall):
        f1 = float("nan")
    else:
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def compute_ece(confidence_correct_pairs, n_bins=10):
    """Expected Calibration Error (Guo et al. 2017; used for exactly this
    purpose -- checking a detector's confidence against empirical accuracy --
    by Rückin et al., "An Informative Path Planning Framework for Active
    Learning in UAV-Based Semantic Mapping", IEEE T-RO 2023, arXiv:2302.03347).
    UW-TIG's whole premise is that its uncertainty/confidence signals are
    worth planning around; this checks whether the detector's confidence is
    actually a trustworthy probability (mean confidence tracks empirical
    accuracy in each bin) rather than just an arbitrarily-scaled score which
    happens to work as a ranking signal but not as a calibrated one."""
    if not confidence_correct_pairs:
        return float("nan")
    conf = np.array([c for c, _ in confidence_correct_pairs])
    correct = np.array([1.0 if ok else 0.0 for _, ok in confidence_correct_pairs])
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(conf)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if not mask.any():
            continue
        ece += (mask.sum() / n) * abs(conf[mask].mean() - correct[mask].mean())
    return float(ece)


def summarize_run(planner_name, scenario_name, seed, mission_logs, scenario):
    counts = {"any": [0, 0, 0], "confirmed": [0, 0, 0]}  # [tp, fp, fn] at the report level
    legacy_tp = legacy_fp = legacy_fn = 0  # pre-fix scoring, kept for transparency (see RESULTS.md)
    cumulative_views = {}  # (wall, label) -> looks so far, carried across missions like persistent memory
    loc_errors = []
    visited_walls_ever = set()
    gt_walls_ever = set()
    revisit_count = {}
    defect_first_last = {}  # defect_id -> (first_uncertainty, last_uncertainty, first_size, last_size, n_obs)
    conf_correct_pairs = []  # (confidence, is_tp) for every raw detection, for ECE
    uncertainty_by_correctness = {"tp": [], "fp": []}  # TTA-ensemble uncertainty split by correctness
    total_dist = sum(m["total_dist"] for m in mission_logs)
    total_viewpoints = sum(m["n_viewpoints"] for m in mission_logs)
    n_cells_total = sum(n_cells_for_wall(w) for w in WALL_SEGMENTS)
    final_entropy = mission_logs[-1]["final_mean_entropy"] * n_cells_total

    for m in mission_logs:
        primary, present = _gt_sets(m["ground_truth"])
        gt_walls_ever |= {w for w, _ in primary}
        mission_max_conf = {}  # (wall, label) -> best confidence this mission
        legacy_hits = set()

        for step in m["steps"]:
            visited_walls_ever.add(step["wall"])
            if step["wall"] in {w for w, _ in primary}:
                revisit_count[step["wall"]] = revisit_count.get(step["wall"], 0) + 1
            labels_this_look = set()
            for det in step["detections"]:
                pair = (step["wall"], det["label"])
                is_correct = pair in present
                conf_correct_pairs.append((det["confidence"], is_correct))
                uncertainty_by_correctness["tp" if is_correct else "fp"].append(det["uncertainty"])
                mission_max_conf[pair] = max(mission_max_conf.get(pair, 0.0), det["confidence"])
                labels_this_look.add(pair)
                if pair in primary:
                    legacy_hits.add(pair)
                    center = scenario._centers.get(step["wall"])
                    if center is not None:
                        gt_xyz = geo.texture_uv_to_world(WALL_BY_NAME[step["wall"]], *center)
                        loc_errors.append(float(np.linalg.norm(np.array(det["world_xyz"]) - gt_xyz)))
                else:
                    legacy_fp += 1

                did = det["defect_id"]
                rec = defect_first_last.setdefault(did, [det["uncertainty"], det["uncertainty"],
                                                          det["size_m"], det["size_m"], 0])
                rec[1] = det["uncertainty"]
                rec[3] = det["size_m"]
                rec[4] += 1
            for pair in labels_this_look:  # one look counts once, however many boxes it drew
                cumulative_views[pair] = cumulative_views.get(pair, 0) + 1

        legacy_tp += len(legacy_hits)
        legacy_fn += len(primary - legacy_hits)

        reported = {
            "any": set(mission_max_conf),
            "confirmed": {pr for pr, c in mission_max_conf.items()
                          if cumulative_views[pr] >= CONFIRM_MIN_VIEWS or c >= CONFIRM_MIN_CONF},
        }
        for variant, rep in reported.items():
            counts[variant][0] += len(rep & primary)
            counts[variant][1] += len(rep - present)
            counts[variant][2] += len(primary - rep)

    precision, recall, f1 = _prf(*counts["any"])
    precision_c, recall_c, f1_c = _prf(*counts["confirmed"])
    precision_legacy, recall_legacy, f1_legacy = _prf(legacy_tp, legacy_fp, legacy_fn)

    reinspect_targets = [w for w in gt_walls_ever if revisit_count.get(w, 0) > 1]
    reinspection_rate = len(reinspect_targets) / len(gt_walls_ever) if gt_walls_ever else float("nan")

    multi_obs = [r for r in defect_first_last.values() if r[4] >= 2]
    uncertainty_reduction = float(np.mean([r[0] - r[1] for r in multi_obs])) if multi_obs else float("nan")
    growth_detected = float(np.mean([r[3] > r[2] for r in multi_obs])) if multi_obs else float("nan")

    ece = compute_ece(conf_correct_pairs)
    mean_unc_tp = float(np.mean(uncertainty_by_correctness["tp"])) if uncertainty_by_correctness["tp"] else float("nan")
    mean_unc_fp = float(np.mean(uncertainty_by_correctness["fp"])) if uncertainty_by_correctness["fp"] else float("nan")
    uncertainty_gap_fp_minus_tp = mean_unc_fp - mean_unc_tp if not (np.isnan(mean_unc_tp) or np.isnan(mean_unc_fp)) else float("nan")

    return {
        "planner": planner_name, "scenario": scenario_name, "seed": seed,
        "precision": precision, "recall": recall, "f1": f1,
        "precision_confirmed": precision_c, "recall_confirmed": recall_c, "f1_confirmed": f1_c,
        "precision_legacy": precision_legacy, "recall_legacy": recall_legacy, "f1_legacy": f1_legacy,
        "mean_localization_error_m": float(np.mean(loc_errors)) if loc_errors else float("nan"),
        "total_flight_dist_m": total_dist, "total_viewpoints": total_viewpoints,
        "coverage_frac": len(visited_walls_ever) / len(WALL_SEGMENTS),
        "reinspection_rate": reinspection_rate,
        "uncertainty_reduction": uncertainty_reduction,
        "growth_detected_frac": growth_detected,
        "info_gain_per_viewpoint": (n_cells_total - final_entropy) / total_viewpoints if total_viewpoints else float("nan"),
        "ece": ece,
        "uncertainty_gap_fp_minus_tp": uncertainty_gap_fp_minus_tp,
    }


def run_sweep(detector, planners, scenarios, seeds, missions_per_scenario, budget, dump_logs=None):
    rows = []
    dumped = []
    with MemoryStore() as mem:
        for scenario_name in scenarios:
            for seed in seeds:
                for planner_name in planners:
                    scen = SCENARIO_REGISTRY[scenario_name](seed=seed)
                    rng = np.random.RandomState(seed)
                    logs = [run_mission(planner_name, scen, mi, detector, mem, rng, budget=budget, seed=seed)
                            for mi in range(1, missions_per_scenario + 1)]
                    rows.append(summarize_run(planner_name, scenario_name, seed, logs, scen))
                    if dump_logs:
                        dumped.append((planner_name, scenario_name, seed, logs))
                    print(f"  done: {planner_name:22s} {scenario_name:12s} seed={seed}")
    if dump_logs:
        import pickle
        with open(dump_logs, "wb") as f:
            pickle.dump(dumped, f)
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
    cols = ["precision", "recall", "f1", "precision_confirmed", "recall_confirmed", "f1_confirmed",
            "precision_legacy", "recall_legacy", "f1_legacy", "mean_localization_error_m", "total_flight_dist_m",
            "coverage_frac", "reinspection_rate", "uncertainty_reduction", "growth_detected_frac",
            "info_gain_per_viewpoint", "ece", "uncertainty_gap_fp_minus_tp"]
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
               "total_flight_dist_m", "info_gain_per_viewpoint", "ece", "uncertainty_gap_fp_minus_tp"]
    fig, axes = plt.subplots(2, 4, figsize=(20, 8))
    for ax, metric in zip(axes.flat, metrics):
        means = [np.nanmean([r[metric] for r in by_planner[p]]) for p in planners]
        ax.bar(planners, means, color=["#888" if p != "uwtig" else "#2b6cb0" for p in planners])
        ax.set_title(metric)
        ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    path = os.path.join(out_dir, "comparison.png")
    fig.savefig(path, dpi=140)
    print("wrote", path)


def _seed_csv_path(seed):
    return os.path.join(RESULTS_DIR, f"comparison_seed{seed}.csv")


def merge_seed_csvs(seeds, out_path):
    """Concatenates each seed's own CSV (written by a separate `--seed N`
    subprocess -- see run_full_sweep.sh) into the final comparison.csv, then
    prints/plots exactly as a single-process sweep would have. Exists
    because a long-lived single process running the full ~140-mission sweep
    (7 planners x 4 scenarios x 5 seeds) crashed repeatedly in this
    environment (numpy allocation error, silent exit, segfault -- three
    different symptoms across three attempts) with no failure inside the
    planner logic itself, consistent with pybullet's ER_TINY_RENDERER
    software rasterizer accumulating state across ~140 sequential
    connect/render/disconnect cycles (see RESULTS.md Limitation 7 /
    NOVELTY.md). Running one seed per fresh process sidesteps that
    accumulation entirely instead of trying to fix pybullet's internals."""
    rows = []
    missing = []
    for seed in seeds:
        path = _seed_csv_path(seed)
        if not os.path.exists(path):
            missing.append(seed)
            continue
        with open(path, newline="") as f:
            rows.extend(csv.DictReader(f))
    if missing:
        print(f"WARNING: missing seed CSVs for seeds {missing} -- merge is partial")
    for r in rows:
        for k, v in r.items():
            if k in ("planner", "scenario"):
                continue
            r[k] = float(v) if v not in ("", "nan") else float("nan")
        r["seed"] = int(r["seed"])
    write_csv(rows, out_path)
    print_summary_table(rows)
    make_plots(rows, RESULTS_DIR)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--budget", type=int, default=16)
    ap.add_argument("--missions", type=int, default=3)
    ap.add_argument("--quick", action="store_true", help="1 seed, small budget, for a smoke test")
    ap.add_argument("--seed", type=int, default=None,
                     help="Run ONLY this single seed, writing results/comparison_seed{N}.csv "
                          "instead of the merged comparison.csv -- for running the sweep as "
                          "several small subprocesses (see run_full_sweep.sh) instead of one "
                          "long-lived process, to avoid a pybullet resource-accumulation crash "
                          "seen across the full ~140-mission sweep (RESULTS.md Limitation 7).")
    ap.add_argument("--merge", action="store_true",
                     help="Merge results/comparison_seed{0..seeds-1}.csv (from prior --seed N "
                          "runs) into results/comparison.csv and print/plot -- runs no missions.")
    ap.add_argument("--planners", nargs="+", default=None, help="subset of PLANNER_REGISTRY (default: all)")
    ap.add_argument("--scenarios", nargs="+", default=None, help="subset of SCENARIO_REGISTRY (default: all)")
    ap.add_argument("--dump-logs", default=None,
                     help="pickle every run's raw mission logs here -- used on DEV seeds to choose the "
                          "report-confirmation rule offline (experiments/tune_report_rule.py)")
    ap.add_argument("--out", default=None, help="override the output CSV path")
    args = ap.parse_args()

    if args.quick:
        args.seeds, args.budget, args.missions = 1, 8, 2

    if args.merge:
        merge_seed_csvs(list(range(args.seeds)), os.path.join(RESULTS_DIR, "comparison.csv"))
        sys.exit(0)

    from perception.ml_detector import detect_with_uncertainty as detector

    planners = args.planners or list(PLANNER_REGISTRY.keys())
    scenarios = args.scenarios or list(SCENARIO_REGISTRY.keys())
    seeds = [args.seed] if args.seed is not None else list(range(args.seeds))

    rows = run_sweep(detector, planners, scenarios, seeds, args.missions, args.budget, dump_logs=args.dump_logs)
    out_path = args.out or (_seed_csv_path(args.seed) if args.seed is not None
                            else os.path.join(RESULTS_DIR, "comparison.csv"))
    write_csv(rows, out_path)
    if args.seed is None:
        print_summary_table(rows)
        make_plots(rows, RESULTS_DIR)
    else:
        print(f"wrote {out_path} ({len(rows)} rows) -- run with --merge once all seeds are done")
