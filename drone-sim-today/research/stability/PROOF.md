# Exact expected stability duration: a candidate research contribution

Status: a proved model-specific result and executable counterexample, **not a
proof of historical originality**. No claim of first publication is justified.
The new solver is a separate research stage; the flight planner and stages 8–12
still use their documented certificate rules and approximate scoring.

## Precise proposed contribution

Compile finite-horizon, allocated-risk stability certificates into intervals of
a candidate view's scalar innovation. Integrate those intervals analytically to
score expected certified region-days, including benefits to unobserved regions
through shared nuisance covariance, while retaining their physical audit clocks.
This removes observation quadrature from this restricted view-selection problem.
It is not a new Kalman filter, new union bound, or a general POMDP solver.

## Assumptions and certificate

Condition on the complete current observation history. A candidate returns one
scalar Gaussian observation, standardized as Z ~ N(0,1). Each future constraint
target has conditional distribution X_j | Z=z ~ N(m_j+b_j z, v_j-b_j²).
Future process noise is independent of this observation. Constraints, horizons,
and risk allocations are chosen before observing Z. Parameters are known; model
misspecification, unknown jumps, sensor faults, and continuous-time excursions
are outside this theorem.

For a one-sided constraint use margin q=Phi^-1(1-alpha)*sqrt(v-b²).
For a two-sided constraint use q=Phi^-1(1-alpha/2)*sqrt(v-b²).
Accept when L+q <= m+bz <= U-q, omitting any infinite endpoint.
For two-sided constraints this is a conservative split-tail rule, not an exact
inversion of total two-sided Gaussian probability. Exactness below concerns
the expected duration of **this rule**.

## Proposition 1: finite-grid conditional risk

Allocate alpha_j so their sum across all constraints in a region's complete
horizon is at most epsilon. Every issued prefix satisfies all its constraints
with conditional probability at least 1-epsilon.

Proof: each accepted one-sided constraint fails with probability at most alpha_j;
each two-sided constraint has two tails bounded by alpha_j/2. Apply the union
bound to the accepted prefix, whose allocation sum cannot exceed the full sum.
Temporal or inter-region independence is not required. For a fleet-wide bound,
also sum the regional budgets. Repeated issuance does not inherit a lifetime
epsilon guarantee: that requires a separately specified risk-spending policy.

## Proposition 2: exact preposterior duration

Each accepted constraint defines an interval I_j in z, including empty or
unbounded intervals. With b=0 it is either the whole real line or empty. Let
J_k be the intersection of all constraints through day k, including day zero.
Then J_(k+1) is a subset of J_k. Define D as the longest accepted prefix, capped
by H = max(0, maximum audit gap - actual time since direct inspection).

Then E[D] = sum(k=1..H) [Phi(upper(J_k))-Phi(lower(J_k))].

Proof: affine inequalities give intervals by division, reversing signs when b<0.
Prefix intersections are nested. The event D>=k is exactly Z in J_k. Apply the
tail-sum identity for a nonnegative bounded integer random variable. This gives
the formula, evaluated in O(number of constraints) time and O(1) streaming space
(the implementation retains intervals for auditing). Floating-point CDF accuracy
is the only integration error; there is no sampling approximation.

Linearity of expectation permits summing region-days even when every region
depends on the same Z. It does **not** give the probability that all regions
remain safe or independent region outcomes. Fixed costs can be subtracted or
used as divisors; maximizing the resulting scalar scores is exact only for that
one-step objective and supplied finite scalar-view candidates.

## Proposition 3: physical audit clocks cannot be extended remotely

`remote_view_score` never changes a last-direct timestamp and caps H by its
remaining audit age. Consequently even a perfectly informative shared-reference
view cannot produce positive duration beyond that region's physical audit cap.
This is a structural invariant, not a probabilistic assertion.

## Reproducible quadrature ranking failure

Run `python -m research.stability.proof_demo` from the project code root.
Two equal-cost, one-day certificates accept innovations in A=[.2,.3] and
B=[-.01,.01]. Exact expected durations are approximately .03865 and .00798.
Three-node Gaussian quadrature samples {-sqrt(3),0,sqrt(3)} with weights
{1/6,2/3,1/6}; it assigns A=0 and B=2/3 and selects the wrong candidate.
These are legitimate degenerate conditional Gaussians (v=b²); sufficiently
small positive residual variances preserve the strict ranking reversal.
This proves a failure of that approximation, not a performance advantage on
all environments. The unit tests also compare against independent Monte Carlo.

## Prior-art boundary and falsification plan

| Prior work | Already established | Narrow distinction to investigate |
|---|---|---|
| [Fauriat & Zio, 2020](https://www.sciencedirect.com/science/article/pii/S0951832020306347) | Inspection timing driven by value of information | Exact innovation-interval duration computation with anchored multi-region evidence |
| [Huan & Marzouk, 2016](https://arxiv.org/abs/1604.08320) | Sequential Bayesian experimental design | Restricted closed-form objective, not a new design framework |
| [Bect et al.](https://arxiv.org/abs/1608.01118) | Gaussian sequential design, excursion/level-set uncertainty reduction | Prefix duration and hard physical audit age; excursion-set acquisition is close prior art |
| [Sensor selection with correlated noise](https://arxiv.org/abs/1508.03690) | Correlation-aware sensing and scheduling | Objective is certified future duration, not Fisher information |
| [Inspection using imperfect/incomplete data](https://www.cambridge.org/core/journals/data-centric-engineering/article/decisiontheoretic-inspection-planning-using-imperfect-and-incomplete-data/2E36A47DA1F8819B0AF58C6D4032C9D0) | Cross-structure Bayesian dependencies and inspection decisions | Shared observation renews bounded duration without resetting local direct inspection age |

This is a scoped source review, not exhaustive full-text clearance. The interval
algebra and tail-sum identity are elementary established tools. The candidate
contribution is their specific compilation into the anchored NBV objective.
If earlier work already derives this same objective and compiler, withdraw the
algorithmic novelty claim and retain the implementation as an application.

Before a paper claim: review citing/cited papers on look-ahead excursion-set
acquisition, chance-constrained sensing and self-triggered estimation; compare
against accurate adaptive integration using the **same** certificate rule;
evaluate wall-clock scaling and ranking error on randomized beliefs; compare
mission outcomes against strong inspection-timing baselines under identical
actions and risk budgets. The current additive demo's savings do not validate
this new solver because it uses a different rule and includes two-reading views.

## Integration boundaries

`exact_renewal.py` provides generic constraints plus a physical health/change
adapter for the current memory model. The adapter excludes jump hazard and
calibration validity, and does not issue production deferrals. Dependency
revocation must block issuance separately. Existing max-audit behavior was also
fixed to reject already-overdue regions, even when their Gaussian estimate is
confident. Multi-reading complementary views require multivariate probability
integration; they cannot silently use this scalar theorem.
