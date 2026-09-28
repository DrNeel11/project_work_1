# When should the drone *not* scan?

Open [the offline demo](demo/index.html). It is a synthetic research instrument; the actual repository adapter is documented in [STABILITY_NOVELTY.md](../../STABILITY_NOVELTY.md).

## Model and mechanism

There are four regions: a well-estimated stable panel, an uncertain seam, a growing crack, and a stable bracket. The joint Gaussian state contains each region's condition h, change rate r, and last-direct-observation anchor a, plus a shared imaging bias n. Historical mixed observations induce correlations between regional condition estimates and n.

Prediction advances h by r and increases uncertainty through condition, rate and bias process noise. No observation is synthesized while a region is unvisited. For a future integer day k:

```
E[h(t+k)] = mean_h + k mean_r
Var[h(t+k)] = P_hh + 2k P_hr + k² P_rr
               + k q_h + k(k-1)(2k-1) q_r / 6
Var[h(t+k)-a] = Var[h(t+k)] + P_aa - 2(P_ha + k P_ra)
```

The covariance with the historical anchor matters: an uncertain absolute appearance does not imply an equally uncertain change, and a shared reference can revise both consistently.

A prospective deferral covers integer days 0..H. For each day, compute the Gaussian probability of condition exceeding the intervention threshold or absolute change relative to the anchor exceeding a tolerance. Sum the event probabilities across days, then add `1-(1-hazard)^(age+H)` for a modeled allowance for arbitrary unobserved jumps. Accept the largest H whose conservative union bound is within the physical risk budget, also respecting the maximum direct-audit age.

Dependency-aware policies additionally bound deviation of the shared bias from its last reference estimate, summed over the same days. Physical and calibration budgets are separate (5% each by default); do not describe their combination as a 95% guarantee. The sum provides at best a 10% combined event bound under the model assumptions. This is a daily-grid, model-conditional probability bound, not a continuous-time or empirically calibrated safety certificate.

The selected deferral deadline is stored after actual evidence. Advancing the clock cannot renew it. A publicly reported sensor event broadens bias uncertainty for every policy; dependency-aware policies also invalidate the shared support version. A new reference can renew correlated beliefs but cannot reset last-direct acquisition times or evade audit limits.

## View choice

Available actions are a regional mixed observation h+n, a complementary pair h+n and h-n, and a shared-reference observation n. Noises are Gaussian with stated synthetic variances. Pair cost is 1.8 units, regional cost 1, reference cost .6; daily budget is 3 units. These are acquisition costs, not a drone energy or geometry model.

For each view, approximate its outcome distribution with three-point Gaussian quadrature per reading, update the joint posterior, and recompute admissible deferrals. The current renewal score is:

```
(E[additional deferral-days over currently due regions]
 + 4 E[number of due regions resolved]) / acquisition_cost - 1
```

This is an explicit heuristic, not exact lifetime maintenance VoI. Negative outcome contributions are included. The coefficient 4 is a fixed demonstration choice, not a fitted physical constant. The subtraction by 1 does not change rankings among acquisitions, and the due-region policy still acts even if all acquisition scores are negative. It is not a solved optimal stopping problem.

Hard acquisition priority is given to regions whose current physical bound fails or whose direct audit is due. This prevents a known changing region being starved by repeatedly renewing easy healthy regions. If the budget cannot service all due regions, the demo reports overdue-region days; it does not claim deadlines were satisfied.

The myopic information comparator has the same state, action set, costs, dependencies and mandatory priorities. It chooses by reduction in summed marginal Gaussian entropies for due conditions and shared bias. It is a tractable uncertainty baseline, not an exact joint-information or multistep POMDP solver. The predictive-only baseline uses a fixed complementary acquisition, so differences against it combine scheduling and view selection.

## Surprises, intervention and evaluation

A regional observation more than four predictive standard deviations from expectation broadens local condition/rate uncertainty before a single assimilation. This is a heuristic change-point fallback, not a calibrated changepoint posterior. All policies use it. No unannounced simulated jump is passed directly to any planner.

After a regional acquisition, posterior probability of exceeding the intervention threshold above .5 triggers an idealized service reset. That reset changes the simulated physical condition/rate, costs 6 units and resets local memory. These are synthetic intervention assumptions. A scan alone never changes the physical condition. `false_service` means intervention occurred before true condition crossed this chosen threshold, not necessarily that preventive maintenance was undesirable.

Metrics include regional acquisitions, actual regional image count (pairs produce two), reference scans, acquisition cost, idle days, and unrepaired critical region-days sampled at the end of each day. The latter is threshold exposure, not a real failure rate. Overdue-region days use each policy's own due rule; the intentionally frozen-confidence baseline can report zero overdue days while missing deterioration, so that metric cannot be interpreted alone.

Default seed 17, 48 days: renewal NBV scans the two stable regions three times each and the growing crack ten times. In the steady scenario it uses 22 regional images plus 3 reference images, at cost 23.4, with zero critical region-days. Fixed revisits use 90 regional images at cost 81. In the unannounced-jump scenario, renewal's longer gaps produce eight critical region-days, versus three for fixed revisits. Report that detection-delay tradeoff alongside savings.

The embedded 12-seed checks are small synthetic samples, with individual metrics retained in `demo/results.json`. They are not evidence of worldwide originality or field superiority.

## Reproduce

From `drone-sim-today`:

```text
python -m research.stability.demo --days 48 --max-gap 16 --seed 17 --benchmark-seeds 12
python -m unittest discover -s tests -v
node research/stability/smoke.cjs
```

The generated HTML is self-contained. The smoke check exercises controls with a minimal DOM adapter; browser layout is not visually verified. `--max-gap` lets you test the savings/detection-delay tradeoff; the demo is precomputed, so rebuild after changing it.

## What must be established next

The candidate contribution is the view-level renewal objective over shared, revocable stability evidence. Ordinary risk-based revisit scheduling is established. Compare against multi-region VoI/POMDP planning with the same observation model, and ablate reference sharing, covariance retention, renewal scoring, hazard floor, and audit cap. Use repeated real-image sequences to calibrate condition/rate likelihoods and acquisition quality before emitting real-region certificates. Evaluate unseen lighting, pose drift, rapid degradation, and hidden abrupt changes. Extend the 2D/flight candidate graph with actual reference-target visibility and return-budget constraints before claiming an integrated drone system.
