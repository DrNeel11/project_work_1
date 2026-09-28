# CONTRAST-NBV: complementary views for maintenance decisions

Research proposal and executable reference experiment. The proposed research contribution is unverified; this repository is not a deployable drone system.

**New: [open the additive interactive demo](demo/index.html).** It adds eight NBV/memory capabilities sequentially, with replay, exact outcome evaluation, crossed ablations, sparse pair planning and a conservative regret bound. Read [the demo guide](DEMO.md) and [the novelty evidence plan](NOVELTY.md). Rebuild with `python build_demo.py`; run the sampled-history experiment with `python benchmark_demo.py`.

The discussion below preserves the original full-system research direction and the original `nbv.py` experiment. The expanded implementation is in `demo_model.py`; its finite-state covariance proxy is a prototype of, rather than the complete geometry/Jacobian method proposed below.

The central question is: **Which physically feasible pair of views can distinguish deterioration from a persistent imaging artifact well enough to change a maintenance decision?**

For example, an oblique image may contain a crack-like feature consistent with either damage or a reflection. A second view of a nearby reference region may identify the reflection field. Neither image alone settles the maintenance question. Together they can. This motivates planning complementary observations, including views away from the apparent defect.

## Why revise the supplied proposal?

Memory, degradation models, and maintenance value of information are useful, but they do not establish novelty. Inspection and maintenance POMDPs already optimize observation and intervention policies [1,2]. Nuisance-aware active learning [3], sequential experimental design [4], calibration NBV [5], and photometric viewpoint selection [6] further narrow the gap.

There is also a mathematical problem with rewarding expected reduction in failure probability from an observation alone. Under a coherent Bayesian model, E[P(failure | observation)] = P(failure). Observation changes knowledge; intervention changes the physical outcome. Optimize expected loss after choosing an intervention, rather than expected reduction in the posterior mean failure probability.

Blur and glare are not automatically irreducible noise. An unknown but persistent illumination field is a latent nuisance variable that additional views may identify. Independent measurement noise and persistent shared bias must be represented differently.

## Proposed full system

Maintain a joint belief b over component damage d, degradation rate r, shared appearance parameters n, and uncertain camera/registration parameters q. Preserve dependencies between these variables; independent per-image confidence scores discard the correlations that make complementary views useful.

Between missions use a stochastic deterioration transition, for example d(t+dt)=d(t)+r(t)dt+w, with maintenance resets explicitly modeled. Historical evidence should retain its acquisition pose, lighting, calibration, and component association. A change in appearance must compete with the hypothesis of a change in physical condition.

An acquisition action specifies pose, sensor setting, and exposure. Its observation model is p(y | d,r,n,q,a). Candidate generation must enforce visibility, resolution, collision clearance, travel budget, and a return reserve. Safety is a feasibility constraint rather than an arbitrary negative reward.

Let R(b)=min_m E_b[L(m,d,r)] be terminal maintenance Bayes risk, including failure before a specified next service date. The exact finite-horizon objective is:

```
V_0(b,x,B) = R(b)
V_H(b,x,B) = min(
    R(b),
    min over feasible a:
        c(x,a) + E_y[V_(H-1)(Bayes(b,a,y), x_a, B-e(x,a))]
)
```

The stop action is essential. Cost c and maintenance loss must use compatible units; e is a separate resource expenditure. This recursion is standard Bayesian decision theory, not a new contribution.

### The algorithmic research target

Searching all view pairs with nested inference is expensive. Develop a **decision-conditioned complementarity graph** to propose a small number of pairs for accurate belief-space evaluation:

1. Generate physically feasible poses and sensor configurations.
2. Sample damage/nuisance hypotheses from persistent joint memory. Focus pair proposal on hypotheses that recommend different maintenance actions.
3. Linearize predicted observations around each hypothesis. For a view set A, stack damage and nuisance Jacobians. Compute the damage information remaining after nuisance marginalization using the Schur complement of the joint information matrix. Include prior precision; do not invert a singular nuisance block without regularization.
4. Connect views whose combined measurements resolve maintenance-relevant damage directions that remain ambiguous individually. Weight proposals by predicted disagreement resolution and route feasibility. Include reference-region views, historical-pose revisits, and alternative illumination settings.
5. Evaluate the top K proposals with the actual nonlinear observation model and two-step adaptive Bayes risk. Execute only the first acquisition, update the joint memory, and replan. The second acquisition depends on the first outcome.
6. Retain exploratory candidates outside the local approximation. A Jacobian filter can miss multimodal ambiguity; it cannot certify that rejected pairs have no value.

One diagnostic is pair synergy:

```
G(A) = R(b) - E[R(b | observations from A)]
S(a,b) = G({a,b}) - G({a}) - G({b})
```

Positive synergy diagnoses complementarity, but is not an extra reward. Rank final policies by expected total cost to avoid double counting information. The graph proposes experiments; it does not replace Bayesian inference.

**Candidate contribution:** a geometry-grounded, maintenance-conditioned pair proposal method that approaches exhaustive nonmyopic planning at lower computation, while preserving persistent nuisance correlations across inspections. Neither nonmyopic planning nor pair complementarity alone is claimed as new. A systematic review may still invalidate this narrower claim.

## What is implemented

`nbv.py` is a dependency-free, exact discrete reference model:

- Joint belief over binary critical damage and a persistent binary appearance artifact.
- Three abstract view actions with explicit noisy likelihoods.
- Exact Bayesian updates, optional stopping, and adaptive two-step planning.
- No-inspection, damage-entropy, and myopic maintenance-VoI baselines.
- Exact expected-cost evaluation over all possible observation outcomes.
- Six prior settings, including controls where the artifact is known.

The contrast view observes damage XOR artifact, the reference view observes artifact, and the direct view observes damage noisily. XOR deliberately constructs an identifiability counterexample; it is not an optical image formation model. View noises are conditionally independent given the shared state. Each candidate can be acquired once, with at most two acquisitions. Repair costs 20 and eliminates the terminal damage loss; deferring critical damage costs 100; each acquisition costs 1.

Run with Python 3.12 (standard library only):

```
python nbv.py
python -m unittest -v
```

For damage prior 0.2 and artifact prior 0.5:

| Policy | Expected total cost | Expected acquisitions |
|---|---:|---:|
| No inspection | 20.0000 | 0 |
| Damage entropy | 14.6000 | 1 |
| Myopic maintenance VoI | 14.6000 | 1 |
| Exact two-step planning | 7.2544 | 2 |

These are exact model expectations, not empirical field results. The entropy baseline stops at zero damage-information gain and does not optimize monetary cost. The two-step planner has greater lookahead, so its advantage is not evidence for a novel solver. With a known artifact, myopic and two-step planners both achieve 5.64 in the corresponding control.

Four tests verify Bayesian probability conservation, zero individual damage information with positive pair value, solver/evaluator agreement, and stopping behavior.

The original `nbv.py` does not implement the complementarity graph or temporal transitions. The newer `demo_model.py` adds a covariance-based pair graph, discrete temporal memory, schematic 2D travel constraints and diagnostic bounds. Continuous geometry, physical image rendering, learned likelihoods, flight dynamics, multi-component allocation and hardware integration remain unimplemented.

## Experiments needed to earn a novelty claim

First construct a rendered benchmark with repeated component inspections, physical defect growth, shared lighting/material changes, pose errors, and disjoint training/test assets. Obtain repeated real multi-view images with independently measured defect sizes. Split by asset and acquisition session rather than neighboring frames.

Compare equal budgets and candidate sets against coverage NBV, target and joint entropy, myopic maintenance VoI, random/nearest feasible views, generic depth-two belief-space search, and exhaustive pair search on tractable instances. The generic nonmyopic baseline is crucial: beating greedy NBV alone cannot validate the graph contribution.

Ablate nuisance correlation, temporal memory, decision conditioning, pair proposals, and adaptive second-view selection. Include clean surfaces, known nuisance, rapidly changing nuisance, wrong likelihoods, identity errors, and scenes where useful pairs do not exist. Report maintenance loss, missed critical defects, unnecessary repairs, calibration, flight cost, planning latency, and regret against exhaustive search. Pair all methods on identical latent scenes and report uncertainty across independent assets/seeds.

The proposal fails if an ordinary depth-two planner matches it at comparable compute, if the graph loses useful pairs, if benefits disappear with realistic rendering, or if nuisance inference is too miscalibrated to improve decisions. Report those outcomes rather than selecting only complementary toy scenes.

## Primary-source starting points

This is a targeted scoping search, not a completed systematic novelty review.

1. Memarzadeh & Pozzi (2016), [Value of information in sequential decision making: Component inspection, permanent monitoring and system-level scheduling](https://www.sciencedirect.com/science/article/pii/S0951832016300771).
2. Papakonstantinou & Shinozuka (2014), [Planning structural inspection and maintenance policies: POMDP implementation](https://www.sciencedirect.com/science/article/pii/S0951832014000684).
3. [Bayesian Active Learning in the Presence of Nuisance Parameters](https://arxiv.org/abs/2310.14968).
4. [Sequential Bayesian optimal experimental design via approximate dynamic programming](https://arxiv.org/abs/1604.08320).
5. [Next-Best-View Selection for Robot Eye-in-Hand Calibration](https://arxiv.org/abs/2303.06766).
6. [Photometric visibility matrix for the automatic selection of optimal viewpoints](https://ieeexplore.ieee.org/document/10550448/).

Before publication, trace forward and backward citations for these works and search specifically for decision-focused experimental design, active defect disambiguation, correlated observation errors, multiview inspection, and informative path planning with complementary measurements.
