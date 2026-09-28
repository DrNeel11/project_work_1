# What would establish novelty?

The current project has a working research instrument and a candidate algorithm, not an established originality claim. We can prove properties under stated assumptions, demonstrate empirical advantages, and document distinctions from published methods. We cannot prove that no related idea exists anywhere.

The intended claim is narrow:

> Persistent damage–artifact memory can guide inexpensive view-pair proposals for maintenance planning, reducing costly observation-tree evaluation while bounding the loss from omitted pairs.

The actual scientific burden is showing that this proposal mechanism earns an advantage over a generic, well-implemented belief-space solver with the same memory, objective, horizon, constraints, and compute budget. Renaming a POMDP or combining familiar ingredients does not meet that burden.

## 1. Claim ledger

| Claim | Status | Evidence needed or available |
|---|---|---|
| Maintenance value of information is new | Rejected | Existing inspection/maintenance POMDP work [1] |
| Nuisance-aware sensing is new | Rejected | Explicit nuisance active-learning literature [2] |
| Multi-view lookahead is new | Rejected | Sequential experimental design and nonmyopic robotics [3,4] |
| Sparse planning with performance bounds is new | Rejected | DESPOT, SITH-BSP and alternative observation-space planning [5–7] |
| Marginal memory can lose decision-relevant information | Proved as a counterexample below | `test_joint_memory_counterexample` |
| Useful view pairs can have individually useless views | Proved as a counterexample below | Original `nbv.py` and its complementarity test |
| Restricted pair policies have a computable conservative regret bound | Proved below for this finite model | Bound checks against exhaustive planning; ordinary relaxation argument, not a novelty claim |
| The proposed shortlist preserves cost on these small experiments | Observed | Six teaching scenarios and 64 sampled synthetic histories |
| The proposal is distinct from the closest prior algorithms | Open | Full algorithm/equation audit, citation tracing, implementation comparison |
| It improves the practical cost–runtime frontier | Preliminary only | Matched solver comparison at equal error tolerance and realistic observation cost |
| It helps real repeated inspections | Open | Repeated multi-view acquisitions with independent physical defect measurements |

## 2. Closest prior work and what it rules out

Scoping search performed on 2026-09-28. Reading depth is stated to avoid turning abstract-level comparisons into claims of absence. The descriptions below are positive statements about the sources; an unmentioned feature is not evidence that the paper lacks it.

| Source | What overlaps | Consequence for our claim | Reading depth |
|---|---|---|---|
| [1. Memarzadeh & Pozzi, 2016](https://www.sciencedirect.com/science/article/pii/S0951832016300771) | Sequential inspection and maintenance VoI | Decision-based inspection utility is established | Abstract and publisher section excerpts |
| [2. Sloman et al., UAI 2024](https://arxiv.org/abs/2310.14968) | Target estimation under nuisance uncertainty; nuisance estimation may be necessary | Looking at a reference region to understand an artifact is not by itself new | Abstract and accessible full-text page |
| [3. Huan & Marzouk, 2016](https://arxiv.org/abs/1604.08320) | Sequential experiment design with feedback and future effects | Two-step Bayesian lookahead is established | Abstract and accessible full-text page |
| [4. Vutetakis & Xiao, APN](https://journals.sagepub.com/doi/full/10.1177/02783649241264577) | A perception graph and nonmyopic view sequencing | A graph of views plus longer-horizon planning is not enough | Abstract and full-text introduction/related-work excerpts; online 2024, journal volume 2025 |
| [5. Ye et al., DESPOT](https://arxiv.org/abs/1609.03250) | Sparse belief-tree approximation, regret analysis, anytime planning | Sparsity and regret certification are established | Abstract and conference algorithm excerpt; journal version 2017 |
| [6. Zhitnikov, Sztyglic & Indelman, 2024 version](https://arxiv.org/abs/2310.10274) | Adaptive simplification with guaranteed unchanged optimal action relative to the unsimplified tree | Faster planning without loss of solution quality is established | Abstract; detailed proof-level audit still needed |
| [7. Kong & Indelman, ISRR 2024](https://arxiv.org/abs/2410.07630) | Alternative observation spaces, value bounds, fully observable relaxation | Our perfect-information bound is particularly close to existing simplification machinery | Abstract; detailed proof-level audit still needed |
| [8. Staderini et al., 3DV 2024](https://ieeexplore.ieee.org/document/10550448/) | Photometric visibility for viewpoint selection | Accounting for lighting and reflection in view selection is established | Search abstract and author presentation; publisher full text blocked by browser verification |

For [8], an [author presentation](https://www.messe-stuttgart.de/vision/fileadmin/media/02-programm/Scientific_VISION_Days_2024/09.10.2024_PDFs_Praesentationen/07_SVD_AIT_Vanessa_Staderini.pdf) confirms the photometric planning line of work. No detailed absence claim is made from that presentation.

The main unresolved comparison is to [6] and [7], not only to geometric NBV. If our method is their generic bound-based search with a conventional covariance heuristic, frame the result as an application/benchmark contribution unless a substantive new mechanism is demonstrated.

Search families used include `next best view inspection memory temporal`, `view planning complementarity inspection`, `active perception nuisance planning`, `non-myopic inspection view planning`, `active sensing complementary memory`, and `POMDP simplification upper lower bounds`. Next, trace backward and forward citations from [2], [6], [7], and [8]; record equations, assumptions, observation correlations, pruning rules, and computational costs in a comparison spreadsheet. This is not yet an exhaustive review of all venues or databases.

## 3. Precisely what the prototype does

The eight-state belief is over damage D, degradation-rate category R, and shared artifact polarity N. It predicts future failure probability f(s) from damage and rate. A candidate view has a synthetic, pose-dependent signal g_v(s), independent measurement noise conditional on s, and a three-bin observation model.

The graph proposal uses posterior covariances:

```
k_A = Cov_b(f(s), g_A(s))
C_A = Cov_b(g_A(s), g_A(s)) + diag(sensor_variances)
proxy_gain(A) = k_A C_A^-1 k_A^T
proposal_score({a,b}) = proxy_gain({a,b}) / cheapest_feasible_route_cost
```

This is the reduction in linear-regression mean-square error for predicting f from unquantized noisy signals. It is an exact variance expression for the best linear predictor, not the exact information gain or Bayes-risk reduction for the quantized, multimodal observation model. For Gaussian models it agrees with the corresponding conditional-covariance construction. These are standard estimation facts.

The implementation scores all feasible unordered pairs with that proxy, keeps K, and performs exact discrete Bayes-risk evaluation on retained ordered continuations. It also keeps every singleton policy and stopping. After the first real observation, it replans the final view over all feasible candidates. Thus the executed receding-horizon policy can improve on its original restricted-plan upper bound.

The shortlist is memory- and future-risk-conditioned. It does **not** currently use the repair threshold in its proposal score: changing repair cost alone may change final selection without changing the shortlist. A stronger genuinely decision-conditioned proposal is a future research target; it must be compared against this simpler proxy.

The original README describes a broader geometry/Jacobian proposal. This prototype instead instantiates a finite-state covariance surrogate so the algorithm can be inspected and falsified now. It does not implement a physical optical renderer, continuous pose optimization, or general collision checking.

## 4. Mathematical evidence we can establish now

### A. Marginals are not sufficient in general

Consider two joint memories over binary D,N:

```
b+ : P(0,0)=P(1,1)=1/2
b- : P(0,1)=P(1,0)=1/2
```

Both have identical damage and artifact marginals. A noiseless reference observation N=1 implies D=1 under b+ and D=0 under b-. With repair loss 20 and defer loss 100D, the optimal actions are repair and defer respectively.

Any memory representation that contains only these marginals maps b+ and b- to the same representation. Given the same reference observation, a deterministic updater must produce the same action for both and therefore cannot reproduce both optimal decisions. A randomized updater also cannot be optimal in both, because their unique optimal actions differ. This proves a limitation of marginal-only storage, not that all tasks require a full joint posterior.

### B. One-step value can miss complementary measurements

Let D,N be independent fair bits. View A returns D XOR N and view B returns N. Each alone is independent of D, so neither changes the maintenance Bayes risk. Together they reveal D. With the same loss, stopping costs 20 and perfect information yields expected terminal loss 10. If each acquisition costs c with 0<c<5, the pair costs 10+2c<20 while either singleton costs 20+c>20.

Therefore positive pair value does not imply positive singleton value. A policy that prunes every individually unhelpful view can discard the optimal pair. The noisy original `nbv.py` experiment is an executable variant. This familiar synergy construction proves the failure mode, not novelty of nonmyopic sensing.

### C. Restricted-search sandwich

Let V* be optimal two-step cost, U_K the best policy restricted to K proposed pair edges plus every singleton and stopping, and V_1 the optimal one-step-then-stop cost. Under the same belief/model/feasibility rules:

```
V* <= U_K <= V_1.
```

Proof: these are minimizations over nested policy sets. K=0 gives V_1. Keeping every feasible edge gives V*. Increasing K in a fixed ranked list cannot increase U_K. The **executed** policy replans after the first observation, so its cost is at most U_K; its empirical performance across different K need not be monotonic. V_1 is not the same as evaluating a receding sequence of greedy decisions.

The guarantee concerns expected cost under the model used to plan. It does not protect against an incorrect artifact-drift model.

### D. A conservative certificate without exhaustive second-view evaluation

For posterior b after first view i, define the perfect-latent-information terminal cost

```
P(b) = sum_s b(s) min_m L(m,s).
```

Here L(defer,s)=100 f(s) and L(repair,s)=20. Perfect state information still does not reveal the future random failure realization. For an omitted feasible second view j,

```
q_j(b) >= acquisition_and_travel(i,j) + return_cost(j) + P(b).
```

Proof: even an ideal second view that reveals s cannot yield lower expected optimal maintenance loss than P(b). A real view supplies no more information; costs are fixed and nonnegative.

At each first-view observation branch, take the minimum of: the exact stop cost, exact evaluated second-view costs, and these optimistic omitted-view bounds. Average using the first observation's predictive probabilities and add first-view cost. Minimizing over first views and stopping gives L_K <= V*. The restricted policy cost gives U_K >= V*, hence

```
0 <= U_K - V* <= U_K - L_K.
```

The executed receding-horizon policy also satisfies this regret upper bound under the known model. A zero gap certifies an optimal decision policy for this horizon; a nonzero gap states what is unproven. This relaxation/bounding argument is standard and overlaps particularly with [7]. We are not claiming a new general POMDP theorem.

All bounds are numerical floating-point bounds in the implementation, tested to tolerance; they are not interval-arithmetic certificates. Generalizing to moving latent state within an acquisition sequence requires including acquisition duration and transitions in both the exact and relaxed models.

## 5. Additive demonstration and causal attribution

Use the eight stages in [DEMO.md](DEMO.md), but do not use staircase improvement as the only attribution evidence. An additive order can hide interactions or give one capability credit for another.

The demo also runs a 4 x 3 crossed experiment: memory in {none, snapshot, temporal factorized, joint} versus planner in {myopic, exact two-view, sparse graph}. Define the interaction contrast:

```
I = (cost_joint,myopic - cost_joint,exact)
  - (cost_temporal,myopic - cost_temporal,exact).
```

Positive I means lookahead gains more when joint dependencies are preserved. This is a conditional descriptive contrast, not proof of a universal interaction. For a statistical claim, average paired contrasts over independent assets and give confidence intervals clustered by asset.

Useful controls are deliberately included: no history, zero time gap, limited return budget, and unexpected artifact drift. Stages are allowed to tie or get worse. A graph speed claim must report proposal and bound overhead, not just reductions in exact expansions.

## 6. What the current results say

Reproduction: `python build_demo.py` and `python benchmark_demo.py --episodes 64 --seed 20260928`.

On the six teaching cases, K=4 produces the same executed expected costs as exhaustive planning. In five unrestricted 12-candidate cases, root exact expansions drop from 408 to 36, but the graph additionally evaluates 66 proxy pairs and 372 cheap omitted-branch bounds. The restricted root policy can have a worse predicted cost even when replanning subsequently recovers the exhaustive cost. Do not confuse those quantities.

On 48 sampled matched-model histories, mean costs by stage are approximately:

| Coverage | Entropy | Decision | Snapshot | Temporal | Joint | Exact pairs | Sparse pairs |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12.4724 | 11.7881 | 10.9284 | 13.8919 | 10.7699 | 10.7685 | 10.7622 | 10.7622 |

These results show a substantial stale-memory penalty but only tiny average gains from joint memory and lookahead in this generator. The paired bootstrap intervals for those latter improvements touch zero. The proposed graph ties exhaustive search in all 64 sampled episodes; a degenerate bootstrap interval [0,0] is a statement about that observed sample, not universal equivalence.

In the 16 drift episodes, exhaustive planning under the wrong model is slightly worse on average than myopic joint-memory planning. This illustrates the distinction between planning accuracy and model accuracy.

**Scientific interpretation:** the current generator is too easy or too narrow to establish the practical importance of the candidate contribution. The artifacts are useful for mechanisms, implementation checks, and experiment setup. They do not yet justify a paper claim of a new general NBV method.

## 7. Gates for a defensible paper claim

1. **Prior-art distinction.** Finish equation-level audits of [2], [6], [7], [8] and their citation neighborhoods. State the specific operation/assumption their methods lack; avoid broad “first memory-aware NBV” language. If our operation is equivalent after variable renaming, withdraw that novelty claim.
2. **Mechanism necessity.** Use rendered physical scenes with a measured ambiguity between defect change and appearance change. Demonstrate matched-history cases where joint memory changes acquisition choices or maintenance decisions. Do not tune only to XOR-like scenes.
3. **Algorithmic advantage.** Compare against exhaustive depth-two search, generic bound-guided search using the same perfect-information relaxation, and a suitable published approximate solver under identical compute and view budgets. Include random-K, nearest-K, top-singleton-K, and geometry-only pair proposals. This isolates the proposed ranking from pruning machinery.
4. **Accuracy–compute frontier.** Plot actual maintenance regret, certificate width, failure rates, total runtime, and memory against K and candidate count. Include rendering/likelihood construction in a separate end-to-end timing. Fixed-K is not automatically adequate as problems grow.
5. **Generalization and failures.** Hold out assets, material/lighting conditions, and inspection sessions. Vary defect prevalence, transition rates, nuisance persistence, intervention thresholds, calibration error, registration drift, and the availability of reference surfaces. Freeze parameters before test evaluation.
6. **External evidence.** Acquire repeated views of physical defects and references with independently measured damage. Report acquisition and analysis scripts. Field execution validates physical feasibility; it does not, by itself, validate lifetime failure prediction.

Example success criteria to freeze on development data before an independent test: <=1% relative expected-cost excess against exhaustive search, >=2x total planning speedup, and no material increase in missed critical failures. These are suggested practical thresholds, not established standards or achieved field results. At near-zero baseline cost, use an absolute tolerance instead. Define asset-level confidence intervals and failure noninferiority margins before looking at test outcomes.

If these gates fail, the useful contribution may be the diagnostic benchmark and representation analysis. If they pass, a defensible claim is about the specific memory-conditioned proposal mechanism and its measured operating regime, not every familiar component in the system.
