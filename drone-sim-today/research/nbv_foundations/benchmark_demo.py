"""Paired synthetic-history experiment; optional extension beyond the six teaching cases."""
import argparse
import hashlib
import json
from pathlib import Path
import random
from statistics import mean

from demo_model import (STAGES, STATES, initial, likelihood, make_views,
                        run_stage, transition)


def sample_history(rng, episode, count=12):
    """Exogenous historical acquisitions, independent of the evaluated stage."""
    state = rng.choices(range(8), weights=initial())[0]
    views = make_views(count)
    time, history = 0, []
    flip = .45 if episode % 4 == 3 else .02
    for _ in range(rng.randrange(5)):
        delta = rng.randrange(3)
        point = tuple(float(i == state) for i in range(8))
        state = rng.choices(range(8), weights=transition(point, delta, flip))[0]
        time += delta
        view = rng.randrange(count)
        outcome = rng.choices(range(3), weights=likelihood(views[view], STATES[state]))[0]
        history.append((time, view, outcome))
    return dict(id=f"episode_{episode:04d}", name="Sampled history", description="",
                history=history, now=time+rng.randrange(7), energy=rng.uniform(6., 14.),
                blocked=[i for i in range(count) if rng.random() < .1], flip=flip)


def bootstrap(values, seed, repetitions=1000):
    rng = random.Random(seed)
    means = sorted(mean(rng.choices(values, k=len(values))) for _ in range(repetitions))
    return dict(mean=mean(values), ci95=[means[int(.025*repetitions)], means[int(.975*repetitions)]],
                episodes=len(values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260928)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent/"demo"/"benchmark.json")
    args = parser.parse_args()
    if args.episodes < 8 or not 0 <= args.top_k <= 66:
        parser.error("Use at least 8 episodes and a top-k in 0..66")
    rng, records = random.Random(args.seed), []
    for episode in range(args.episodes):
        scenario = sample_history(rng, episode)
        results = [run_stage(scenario, stage, top_k=args.top_k) for stage in STAGES]
        records.append(dict(scenario=scenario, costs=[r["metrics"]["cost"] for r in results],
                            expansions=[r["work"]["branch_expansions"] for r in results],
                            certificate=results[7]["first"].get("certificate")))
    summaries = {}
    for group, matched in (("matched_model", True), ("artifact_drift", False)):
        subset = [r for r in records if (r["scenario"]["flip"] == .02) == matched]
        comparisons = {}
        for a, b, label in [(i, i-1, f"stage_{i}_minus_{i-1}") for i in range(1, 8)]+[(7, 6, "graph_minus_exact")]:
            differences = [r["costs"][a]-r["costs"][b] for r in subset]
            comparisons[label] = bootstrap(differences, args.seed+a)
        summaries[group] = dict(mean_costs=[mean(r["costs"][i] for r in subset) for i in range(8)],
                                comparisons=comparisons)
    output = dict(seed=args.seed, episodes=args.episodes, top_k=args.top_k,
                  source_hashes={name: hashlib.sha256((Path(__file__).resolve().parent/name).read_bytes()).hexdigest()
                                 for name in ("demo_model.py", "benchmark_demo.py")},
                  scope="Synthetic, independently generated histories; fixed 8-state model and 12 schematic poses. Not field evidence.",
                  interpretation="Paired percentile bootstrap across episodes. Negative differences favor the added stage. Drift group uses a misspecified artifact model; exact means exhaustive under that model, not a truth oracle.",
                  summaries=summaries, records=records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    for group, summary in summaries.items():
        print(group, "mean costs:", [round(c, 4) for c in summary["mean_costs"]])
        print("graph minus exact:", summary["comparisons"]["graph_minus_exact"])
    print(args.output)


if __name__ == "__main__":
    main()
