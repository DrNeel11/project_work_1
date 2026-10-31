"""Ten-seed statistics with the original detector: seeds 0-4 (comparison.csv / large_base) + seeds 5-9 (seeds59_*).
F1 of confirmed reports, mean over static/uncertain/multi_defect per seed; 95% bootstrap CI over the ten seeds."""
import json
import numpy as np
import pandas as pd

SETS = {"small": ["results/comparison.csv", "results/seeds59_small/comparison.csv"],
        "large": ["results/large_base/comparison.csv", "results/seeds59_large/comparison.csv"]}
rng = np.random.default_rng(0)
out = {}
for yard, files in SETS.items():
    df = pd.concat([pd.read_csv(f) for f in files])
    df = df[df.scenario != "growing"]
    per = df.groupby(["planner", "seed"]).agg(f1=("f1_confirmed", "mean"), flight=("total_flight_dist_m", "mean"), cov=("coverage_frac", "mean")).reset_index()
    f1 = per.pivot(index="seed", columns="planner", values="f1")
    res = {}
    for p in f1.columns:
        v = f1[p].values
        bs = [rng.choice(v, len(v)).mean() for _ in range(5000)]
        res[p] = dict(f1=float(v.mean()), ci=[float(x) for x in np.percentile(bs, [2.5, 97.5])],
                      flight=float(per[per.planner == p].flight.mean()))
    for o in f1.columns:
        if o == "uwtig":
            continue
        d = (f1["uwtig"] - f1[o]).values
        bs = [rng.choice(d, len(d)).mean() for _ in range(5000)]
        res[o]["uwtig_minus"] = dict(diff=float(d.mean()), ci=[float(x) for x in np.percentile(bs, [2.5, 97.5])], wins=int((d > 0).sum()), n=len(d))
    out[yard] = res
    print("==", yard, "seeds", sorted(f1.index))
    for p, r in sorted(res.items(), key=lambda kv: -kv[1]["f1"]):
        m = r.get("uwtig_minus")
        print(f"{p:26s} F1 {r['f1']:.3f} [{r['ci'][0]:.3f},{r['ci'][1]:.3f}] flight {r['flight']:.0f}" + (f"  UWTIG-this {m['diff']:+.3f} [{m['ci'][0]:+.3f},{m['ci'][1]:+.3f}] wins {m['wins']}/{m['n']}" if m else ""))
json.dump(out, open("results/ten_seed_summary.json", "w"), indent=1)
