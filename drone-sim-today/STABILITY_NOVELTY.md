# Stability-aware NBV development branch

Branch: `novelty/stability-aware-nbv`, based on `main` commit `341ad2a`.

This branch extends the existing project with the user's requested behavior: regions with evidence of slow change and low predictive uncertainty are scanned less frequently. Unknown, changing or uncertain regions remain eligible. A confident estimate of damage is not treated as confidence in stability.

## Concrete research direction

**Revocable stability evidence with renewal-value NBV.** Each region has a condition/rate belief, a last-direct-observation anchor, a modeled risk budget, an expiry, and named supporting evidence. The planner can inspect the region, acquire complementary views, or check a shared reference. A reference can improve several correlated beliefs and extend their admissible deferrals, without resetting their physical audit ages.

The intended contribution is the coupling of view choice to the **expected number of future region-inspection days recovered by renewing shared evidence**. Condition-risk and maximum-audit deadlines override that savings objective. A reported calibration change revokes dependent evidence immediately; an unannounced physical change is not revealed to the planner.

This is a candidate algorithmic contribution, not a verified first-in-literature claim. Adaptive inspection timing already exists in [Fauriat & Zio's aperiodic VoI inspection policy](https://www.sciencedirect.com/science/article/pii/S0951832020306347). Joint selection of timing and inspection method is also discussed in [uncertainty-based bridge inspection planning](https://www.mdpi.com/2412-3811/6/2/27). Our narrower hypothesis concerns shared, revocable evidence and the view-level deferral-renewal objective. It must be compared against generic multi-region VoI/POMDP scheduling, not just the original Isler baseline.

## Additive demos

1. [Stages 0–7: NBV and memory foundations](research/nbv_foundations/demo/index.html): coverage, information, maintenance value, historical/temporal/joint memory, two-view lookahead and sparse pairs. This carries forward the earlier standalone work.
2. [Stages 8–12: repeated missions and stability](research/stability/demo/index.html): fixed revisits, frozen-confidence ablation, predictive revisit intervals, revocable memory with myopic information NBV, and renewal-value NBV.

The second demo includes a 48-day calendar, evolving means and uncertainty bands, region-specific revisit deadlines, reference dependencies, acquisition choices, cost/detection comparisons, and 12 additional seeds per scenario/policy. Its full mathematical and experimental limitations are in [research/stability/README.md](research/stability/README.md).

## Integration with the existing code

`planning/deferral.py` provides `StabilityCertificate`, a scope-isolated `DeferralLedger`, and `DeferralPlanner`, which wraps an existing planner. A viewpoint is deferred only if **every** cell it observes has currently valid evidence. A mixed view with an unknown/due cell remains eligible. The wrapper does not modify the original planner's candidate list.

`experiments/mission.py::run_mission` now accepts optional `deferrals`, `inspection_time`, and `region_observer` arguments. Default calls and the existing comparison sweep retain their original planner behavior. If every region can be deferred, acquisition stops and logs the actual view count. Memory namespaces distinguish opt-in stability runs from baseline runs.

Example interface (not an automatic YOLO calibration):

```python
from planning.deferral import DeferralLedger

# This scope must exactly match scenario + selected planner + seed.
ledger = DeferralLedger(f"{scenario.name}|uwtig+stability|{seed}")
log = run_mission(
    "uwtig", scenario, mission_index, detector, mem, rng,
    seed=seed, deferrals=ledger, inspection_time=elapsed_days,
    region_observer=validated_region_observer,
)
ledger.save("local_memory/region_deferrals.json")
```

The observer receives `(bgr_frame, viewpoint, inspection_time)` and returns `StabilityCertificate` objects for observed cells. It must have independently calibrated the mapping from observations to condition/rate uncertainty and predictive risk. The adapter checks provenance, time, modeled risk budget, audit limits, scope and dependency versions; it cannot verify the scientific validity of the external model.

**No detector boxes does not mean a clean region.** Existing TTA detection uncertainty is not automatically a calibrated probability of no change or a severity variance. This branch deliberately does not manufacture certificates from YOLO silence. Until a valid region observer is supplied, the empty ledger suppresses nothing. Shared-reference renewal in the Gaussian lab is not yet connected to camera reference-target detection in PyBullet.

The existing flagship physics-flight script is unchanged. This first integration is in the kinematic experiment runner and the standalone research laboratory; it is not a claim of end-to-end flight validation.

## Verification

From `drone-sim-today`:

```text
python -m unittest discover -s tests -v
python -m research.stability.demo
node research/stability/smoke.cjs
python -m py_compile experiments/mission.py planning/deferral.py
```

The numerical tests and research demos require only Python's standard library. The cloned project additionally needs its documented NumPy, PyBullet, detector and database dependencies to execute real missions. Those were not installed or executed during this branch setup.

The original `NOVELTY.md`/`RESULTS.md` report previous UW-TIG work; they do not constitute evidence that the new method is globally novel. No prior comparison result has been overwritten.
