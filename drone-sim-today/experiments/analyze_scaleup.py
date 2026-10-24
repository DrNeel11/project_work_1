"""Summarises the scale-up experiments into results/scaleup_summary.json + .md.

Inputs (results/): large_base (31 walls, original detector), large_new (31 walls,
detector fine-tuned on MBDD + dacl10k + corrosion), small_new (9 walls, new
detector), comparison.csv (9 walls, original detector -- the earlier headline).

For every planner: mean precision/recall/F1 (confirmed reports), flight distance
and coverage over the 3 scored scenarios (static, uncertain, multi_defect; 'growing' is excluded as in every earlier headline) x 5 test seeds, with a 95% bootstrap interval
on F1 taken over *seeds* (each seed's value = mean over its scenarios, so the
unit of resampling is the independent seed, not the correlated rows), plus the
paired per-seed F1 difference of UW-TIG against every other planner.
"""
import csv
import json
import os
import random
import statistics as st

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
SETS = {"small_old": "comparison.csv", "small_new": "small_new/comparison.csv",
        "large_old": "large_base/comparison.csv", "large_new": "large_new/comparison.csv"}
KEYS = ["precision_confirmed", "recall_confirmed", "f1_confirmed", "total_flight_dist_m", "coverage_frac"]


def load(name):
    path = os.path.join(RES, SETS[name])
    if not os.path.exists(path):
        return None
    rows = [r for r in csv.DictReader(open(path)) if r["scenario"] != "growing"]  # growing excluded, as in every earlier headline
    for r in rows:
        r["seed"] = int(float(r["seed"]))
        for k in KEYS:
            r[k] = float(r[k]) if r[k] not in ("", "nan") else float("nan")
    return rows


def seed_means(rows, planner, key, scen=None):
    out = {}
    for s in sorted({r["seed"] for r in rows}):
        v = [r[key] for r in rows if r["planner"] == planner and r["seed"] == s and (scen is None or r["scenario"] == scen)]
        v = [x for x in v if x == x]
        if v:
            out[s] = sum(v) / len(v)
    return out


def boot_ci(vals, n=10000, seed=0):
    rng = random.Random(seed)
    m = [sum(rng.choice(vals) for _ in vals) / len(vals) for _ in range(n)]
    m.sort()
    return m[int(0.025 * n)], m[int(0.975 * n)]


def summarise(rows):
    out = {}
    for p in sorted({r["planner"] for r in rows}):
        d = {k: st.mean([x for x in (r[k] for r in rows if r["planner"] == p) if x == x]) for k in KEYS}
        f1s = list(seed_means(rows, p, "f1_confirmed").values())
        d["f1_ci"] = boot_ci(f1s)
        d["f1_seed_std"] = st.pstdev(f1s)
        d["per_scenario_f1"] = {sc: st.mean([r["f1_confirmed"] for r in rows if r["planner"] == p and r["scenario"] == sc])
                                for sc in sorted({r["scenario"] for r in rows})}
        out[p] = d
    return out


def paired(rows, a="uwtig"):
    out = {}
    fa = seed_means(rows, a, "f1_confirmed")
    for p in sorted({r["planner"] for r in rows} - {a}):
        fb = seed_means(rows, p, "f1_confirmed")
        diffs = [fa[s] - fb[s] for s in fa if s in fb]
        out[p] = {"mean_diff": st.mean(diffs), "ci": boot_ci(diffs), "seeds_won": sum(d > 0 for d in diffs), "n": len(diffs)}
    return out


def main():
    summary = {}
    for name in SETS:
        rows = load(name)
        if rows:
            summary[name] = {"n_rows": len(rows), "planners": summarise(rows), "uwtig_vs": paired(rows)}
    json.dump(summary, open(os.path.join(RES, "scaleup_summary.json"), "w"), indent=1)
    lines = []
    for name, s in summary.items():
        lines += [f"### {name} ({s['n_rows']} rows)", "", "| planner | P | R | F1 | F1 95% CI | flight m | cov |", "|---|---|---|---|---|---|---|"]
        for p, d in sorted(s["planners"].items(), key=lambda kv: -kv[1]["f1_confirmed"]):
            lines.append(f"| {p} | {d['precision_confirmed']:.3f} | {d['recall_confirmed']:.3f} | {d['f1_confirmed']:.3f} | "
                         f"{d['f1_ci'][0]:.3f}-{d['f1_ci'][1]:.3f} | {d['total_flight_dist_m']:.1f} | {d['coverage_frac']:.2f} |")
        lines.append("")
    open(os.path.join(RES, "scaleup_summary.md"), "w").write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
