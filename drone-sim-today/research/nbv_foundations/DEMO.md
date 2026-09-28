# Additive NBV demo

Open [demo/index.html](demo/index.html) in a browser. It is self-contained HTML with embedded results: no server, dependencies, login, or internet connection. Adjacent Markdown and downloadable data links require keeping the repository files together. The browser presents precomputed exact evaluations; it does not run the Python planner live.

## Controls and a suggested walkthrough

Choose a scenario, then use **Add dimension** or the numbered stage buttons. **Play stages** advances every 3.5 seconds. **Acquire view** walks through a reproducible observation trajectory. The world state stays hidden unless revealed. This sampled trajectory is illustrative; the cost chart averages every possible future observation.

Start with “Fresh inspection” to see that stored history adds nothing when none exists. Switch to “Reassuring, then unvisited” to expose stale-memory failure. Use “An ambiguous old image” to see a reference view exploit a damage–artifact dependency. Finally compare stages 6 and 7 under “Limited travel budget” and inspect the K sweep, runtime and regret certificate.

Every stage uses the same view candidates, likelihoods, travel model, intervention losses and two-acquisition cap. Stages 0–5 choose views myopically and replan after each acquisition. Stages 6–7 reason about a second acquisition before selecting the first.

| Stage | Added dimension | Historical memory | NBV rule | What it teaches |
|---|---|---|---|---|
| 0 | Schematic coverage | None | New patches / cost | Geometric completeness is a baseline |
| 1 | Damage uncertainty | None | Damage entropy gain / cost | Information is different from surface area |
| 2 | Maintenance decision | None | Myopic Bayes risk + cost, with stop | Information is worthwhile when it improves a decision enough |
| 3 | Historical snapshots | Time ignored, factorized damage/rate vs artifact | Same as stage 2 | Memory can be harmful when stale |
| 4 | Time and degradation rate | Time propagated, factorized damage/rate vs artifact | Same as stage 2 | Evidence ages; transition assumptions matter |
| 5 | Joint dependencies | Full joint historical posterior | Same as stage 2 | Evidence about artifacts can inform damage |
| 6 | Complementary views | Same as stage 5 | Exhaustive adaptive two-view planning | A familiar strong comparator, not our novelty |
| 7 | Sparse pair proposals + diagnostic bound | Same as stage 5 | Proxy shortlist, exact restricted evaluation | Candidate research contribution; must match quality at lower total compute |

The “additive” story concerns usable capabilities, not increasing the number of simulated hidden variables. All stages face the same hidden world. Geometry/resource constraints are present throughout so an apparent gain cannot come from relaxing feasibility. All stages retain joint evidence within the current mission; stages 3–4 factorize only during historical storage/replay. With no history, stages 2–5 correctly coincide.

## How memory and NBV connect

```
Timestamped historical views + observations
          ↓ Bayesian update and optional temporal propagation
Persistent joint belief over damage, rate and artifact
          ↓ predicted observations and future failure risk
View-pair covariance proposals + feasible routes
          ↓ exact expected maintenance loss for retained policies
Next view (or stop) + bound on omitted-policy loss
          ↓ acquisition
Updated joint belief → replan → repair or defer
```

There is one component and an eight-state joint belief. Future failure probability is 1 for already damaged states, or 1-(1-hazard[R]) over one time unit otherwise. Slow/fast hazards are .015/.16. Damage is irreversible during historical evolution; the latent rate remains fixed. The artifact follows a symmetric two-state chain, with default per-unit flip probability .02. The drift stress case uses .45 in the world while the planner still assumes .02.

Repair costs 20 and avoids the modeled terminal failure loss; deferral costs 100 times future failure probability. An acquisition costs .6 plus .15 per outbound travel distance; return travel costs .15 per distance. Each acquisition consumes .25 travel-resource units in addition to Euclidean movement. Feasibility reserves enough resource to return home. There are no within-mission deterioration transitions, obstacles along travel segments, collision dynamics, imperfect repairs, or multiple maintenance epochs.

Candidate responses are linear in binary damage and artifact polarity plus Gaussian noise, quantized at .25 and .75 into low/middle/high. Pose modulates the schematic response/noise parameters. Contrast views observe mixed damage/artifact; reference views observe artifact; direct views observe damage noisily. This is not a physical image renderer. Schematic coverage patches are a pedagogical baseline, not ray-traced visible mesh areas.

## Reading the panels

- **View map:** candidate poses, proposed pairs, completed route, and intended next move. At stop the dashed route returns home. Unavailable or already acquired candidates are crossed out.
- **Memory:** current marginals and full eight-hypothesis probabilities, plus damage/artifact covariance. The displayed historical record is ignored by no-memory stages.
- **Costs:** exact expected cost under the true conditional world belief, including a possibly different artifact history model. A poorly calibrated planner cannot score itself by its own optimistic confidence.
- **Memory × planning:** crossed ablations and a descriptive interaction contrast. These complement, rather than replace, the additive staircase.
- **K sweep:** executed receding-policy cost, difference from exhaustive planning, the restricted root regret bound, and likelihood expansion count. Root restricted cost and executed cost are different quantities because the second view is replanned.
- **Scaling:** 12, 24, and 48 candidates, five independent root computations each, median runtime. Includes proxy and bound work but excludes constructing the common likelihood table. Candidate families are regenerated at each size, not nested supersets; compare the two policies within each size.
- **Novelty:** distinguishes established ingredients, proved mechanisms, observed results, and open research claims.

The optimal-cost interval and regret bound apply under the planner's model and current belief. In the drift case they do not bound real-world model error. Even a zero interval width cannot validate an incorrect observation/dynamics model.

## Reproduce and extend

From this directory:

```
python benchmark_demo.py --episodes 64 --seed 20260928
python build_demo.py
python -m unittest -v
node smoke_demo.cjs
```

Python 3.12 and the standard library are sufficient to build and run the planner. Node is used only for the optional UI smoke check. That check exercises all scenario/stage/replay combinations with a minimal DOM adapter; it does not verify visual layout in a browser.

Use `python build_demo.py --top-k 8` to regenerate stage 7 with a different graph budget. The precomputed K sweep always includes 0, 1, 2, 4, 8 and all 66 unordered pairs. Change `SCENARIOS` and `make_views` in `demo_model.py` to extend the teaching cases; histories refer to view indices, so preserve those indices or update histories when changing candidates.

The builder embeds sampled-history summaries only when their model source hash and K match the current build. Re-run the benchmark after changing the model; stale benchmark files remain on disk but are not presented as current embedded results.

`benchmark_demo.py` generates independent histories with exogenous historical acquisitions, random elapsed times, random blocked candidates and travel budgets. Three of every four episodes use the matched model; the fourth uses artifact drift. All stages receive the same history and are evaluated over all future observation branches. It reports paired percentile-bootstrap intervals over episodes, separately for matched and drift cases. This is synthetic sampling evidence, not field or population calibration.

## Files and metrics

| File | Purpose |
|---|---|
| `demo_model.py` | Belief, transitions, observations, planners, exact evaluator and replay |
| `build_demo.py` | Generates portable HTML, JSON and CSV, with source hashes |
| `demo_template.html`, `demo_ui.js` | Presentation and controls |
| `demo/index.html` | Ready-to-open offline artifact |
| `demo/results.json`, `demo/results.csv` | Teaching cases, factorial results, K sweep and root work |
| `benchmark_demo.py`, `demo/benchmark.json` | Sampled-history experiment and its complete records |
| `NOVELTY.md` | Claim ledger, literature overlap, proofs and validation gates |
| `test_demo.py`, `smoke_demo.cjs` | Numerical/policy invariants and functional UI smoke test |

`missed` is expected failure probability when deferring, not detector false-negative rate. `unnecessary` is the expected indicator of repair when no failure would otherwise occur in the one-unit horizon. `calibration` is expected squared discrepancy between the planner's predicted failure probability and the true conditional probability after its acquisitions; it is an oracle posterior diagnostic, not empirical ECE or a Brier score. `branch_expansions` counts predictive likelihood expansions, `proxy_pairs` counts scored unordered pairs, and `bound_checks` counts omitted-branch lower-bound evaluations. Raw runtime is machine-dependent.

The original `nbv.py` and `test_nbv.py` remain the compact XOR complementarity experiment. They are separate from the expanded demo's linear, quantized observation model.
