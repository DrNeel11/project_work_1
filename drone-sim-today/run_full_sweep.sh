#!/usr/bin/env bash
# Runs the full evaluate.py sweep as one fresh Python process PER SEED
# instead of one long-lived process, to avoid a pybullet ER_TINY_RENDERER
# resource-accumulation crash seen across the full ~140-mission single-
# process sweep (three consecutive crashes, three different symptoms --
# see RESULTS.md Limitation 7 / NOVELTY.md). Each seed is a fresh
# interpreter, so nothing from pybullet's software rasterizer survives
# between seeds. Retries a seed a few times before giving up on it, since
# even a single seed's ~28-mission run (7 planners x 4 scenarios) has shown
# occasional transient failures in this environment.
set -uo pipefail
cd "$(dirname "$0")"

SEEDS=${1:-5}
BUDGET=${2:-16}
MISSIONS=${3:-3}
MAX_RETRIES=3

for ((seed=0; seed<SEEDS; seed++)); do
    attempt=1
    while true; do
        echo "=== seed $seed, attempt $attempt/$MAX_RETRIES ==="
        ./venv/Scripts/python.exe experiments/evaluate.py --seed "$seed" --budget "$BUDGET" --missions "$MISSIONS"
        status=$?
        if [ $status -eq 0 ]; then
            break
        fi
        echo "seed $seed attempt $attempt failed (exit $status)"
        if [ $attempt -ge $MAX_RETRIES ]; then
            echo "seed $seed FAILED after $MAX_RETRIES attempts -- giving up on it, merge will warn it's missing"
            break
        fi
        attempt=$((attempt + 1))
    done
done

echo "=== merging seed CSVs into results/comparison.csv ==="
./venv/Scripts/python.exe experiments/evaluate.py --seeds "$SEEDS" --merge
