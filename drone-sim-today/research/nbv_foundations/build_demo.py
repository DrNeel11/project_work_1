"""Regenerate the portable offline walkthrough and machine-readable evidence."""
import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from statistics import median
from time import perf_counter

from demo_model import BASE, SCENARIOS, STAGES, STATES, Lab, make_views, run_stage


ROOT = Path(__file__).resolve().parent


def scaling(counts, top_k):
    records = []
    for count in counts:
        for stage in STAGES[6:]:
            times, record = [], None
            for _ in range(5):
                lab = Lab(SCENARIOS[1], stage, count, top_k)
                belief = lab.memory()
                start = perf_counter()
                plan = lab.plan(belief, tuple(range(count)), -1, 13., 2)
                times.append((perf_counter()-start)*1000)
                record = dict(candidates=count, policy=stage.policy, value=plan["value"],
                              branch_expansions=lab.expansions, proxy_pairs=lab.proposal_pairs,
                              bound_checks=lab.bound_checks)
            records.append(dict(record, median_ms=median(times), repeats=len(times)))
    return records


def build(top_k=4):
    data = dict(schema=1, seed=7, top_k=top_k, states=STATES, base=BASE,
                stages=[asdict(s) for s in STAGES], views=[asdict(v) for v in make_views()],
                scenarios=[], scaling=scaling((12, 24, 48), top_k))
    rows = []
    for scenario in SCENARIOS:
        results = [run_stage(scenario, stage, top_k=top_k) for stage in STAGES]
        factorial = []
        for memory in ("none", "snapshot", "temporal", "joint"):
            for policy in ("myopic", "exact", "graph"):
                stage = replace(STAGES[7], memory=memory, policy=policy)
                result = run_stage(scenario, stage, top_k=top_k)
                factorial.append(dict(memory=memory, policy=policy, **result["metrics"]))
        sweep = []
        for k in (0, 1, 2, 4, 8, 66):
            result = run_stage(scenario, STAGES[7], top_k=k)
            sweep.append(dict(k=k, cost=result["metrics"]["cost"],
                              branch_expansions=result["work"]["branch_expansions"],
                              proxy_pairs=result["work"]["proxy_pairs"],
                              certificate=result["first"].get("certificate")))
        data["scenarios"].append(dict(scenario, results=results, factorial=factorial, sweep=sweep))
        for i, result in enumerate(results):
            rows.append(dict(scenario=scenario["id"], stage=i, name=STAGES[i].name,
                             **result["metrics"], **result["work"]))
    sources = ("demo_model.py", "build_demo.py", "demo_template.html", "demo_ui.js")
    data["provenance"] = dict(python="Python standard library; no network at runtime",
                              sources={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                                       for name in sources},
                              evaluation="Exact conditional expectations over future observations; six hand-authored histories, not a representative dataset.",
                              timing="Five fresh root-planning runs per scaling point. Median includes proposal and bound overhead, excludes likelihood-table construction.")
    data["benchmark"] = None
    benchmark_path = ROOT/"demo"/"benchmark.json"
    if benchmark_path.exists():
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        current_hash = hashlib.sha256((ROOT/"demo_model.py").read_bytes()).hexdigest()
        if benchmark.get("source_hashes", {}).get("demo_model.py") == current_hash and benchmark["top_k"] == top_k:
            data["benchmark"] = {key: benchmark[key] for key in ("seed", "episodes", "summaries")}
    output = ROOT/"demo"
    output.mkdir(exist_ok=True)
    encoded = json.dumps(data, indent=2, allow_nan=False)
    (output/"results.json").write_text(encoded+"\n", encoding="utf-8")
    with (output/"results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    template = (ROOT/"demo_template.html").read_text(encoding="utf-8")
    script = (ROOT/"demo_ui.js").read_text(encoding="utf-8")
    html = template.replace("/*__DATA__*/", "const DATA = "+encoded.replace("<", "\\u003c")+";")
    html = html.replace("/*__UI__*/", script)
    (output/"index.html").write_text(html, encoding="utf-8")
    for s in data["scenarios"]:
        exact, graph = s["results"][6:8]
        print(f"{s['id']:12} exact={exact['metrics']['cost']:.4f} graph={graph['metrics']['cost']:.4f} "
              f"branches={exact['work']['branch_expansions']} -> {graph['work']['branch_expansions']}")
    print("Open demo/index.html directly in a browser. No server or package install needed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-k", type=int, default=4, help="Number of proposed undirected pairs (0..66)")
    args = parser.parse_args()
    if not 0 <= args.top_k <= 66:
        parser.error("--top-k must be between 0 and 66")
    build(args.top_k)
