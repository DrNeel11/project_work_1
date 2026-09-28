"""Build the offline multi-mission stability demo; standard library only.

Run from drone-sim-today: python -m research.stability.demo
"""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from statistics import mean

from research.stability.model import POLICIES, REGIONS, SCENARIOS, Settings, run


def build(days=48, seed=17, max_gap=16, benchmark_seeds=12):
    root = Path(__file__).resolve().parent
    settings = Settings(days=days, max_gap=max_gap)
    data = dict(settings=asdict(settings), seed=seed, regions=REGIONS, policies=POLICIES,
                scenarios=[], benchmarks=[], model_sha256=hashlib.sha256((root/"model.py").read_bytes()).hexdigest())
    for scenario in SCENARIOS:
        results = [run(p["id"], scenario["id"], seed, settings) for p in POLICIES]
        data["scenarios"].append(dict(scenario, results=results))
        for policy in POLICIES:
            metrics = [run(policy["id"], scenario["id"], 100+i, settings)["metrics"] for i in range(benchmark_seeds)]
            data["benchmarks"].append(dict(scenario=scenario["id"], policy=policy["id"],
                seeds=list(range(100, 100+benchmark_seeds)), samples=metrics,
                mean_cost=mean(m["acquisition_cost"] for m in metrics),
                mean_missed=mean(m["missed_region_days"] for m in metrics),
                mean_images=mean(m["regional_images"]+m["reference_scans"] for m in metrics)))
    output = root/"demo"
    output.mkdir(exist_ok=True)
    encoded = json.dumps(data, separators=(",", ":"), allow_nan=False)
    (output/"results.json").write_text(encoded+"\n", encoding="utf-8")
    html = (root/"template.html").read_text(encoding="utf-8").replace("/*__DATA__*/", "const DATA="+encoded.replace("<", "\\u003c")+";")
    (output/"index.html").write_text(html, encoding="utf-8")
    for scenario in data["scenarios"]:
        print(scenario["id"], {r["policy"]: r["metrics"]["region_scans"] for r in scenario["results"]})
    print(output/"index.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=48)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--max-gap", type=int, default=16)
    parser.add_argument("--benchmark-seeds", type=int, default=12)
    args = parser.parse_args()
    if min(args.days, args.max_gap, args.benchmark_seeds) < 1:
        parser.error("days, max-gap and benchmark-seeds must be positive")
    build(args.days, args.seed, args.max_gap, args.benchmark_seeds)
