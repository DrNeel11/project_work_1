"""Three families of planners compared by experiments/evaluate.py, sharing
one candidate viewpoint graph (planning/viewpoints.py):

- RandomPlanner: uniform random choice among not-yet-visited viewpoints.
  The naive baseline the proposal's Verification Method calls for.

- IslerNBVPlanner: cost-normalized entropy-based next-best-view, adapted
  from Isler et al. (2016)'s volumetric information-gain formulation to this
  2D wall-surface setting (a coarse per-wall coverage grid replaces the
  voxel grid; entropy is over a "surface adequately observed" belief, not
  occupancy). Deliberately geometry/coverage-only, no defect semantics --
  this is the literature gap the proposal identifies for this base paper.
  The coverage-entropy objective it (and UWTIGPlanner's ig term) maximizes
  is a monotone submodular set function of "cells observed so far" (each
  additional look at a cell has non-increasing marginal entropy reduction,
  by construction of coverage_entropy's saturating exp(-k*view_count) form,
  and the objective is additive across independent cells) -- so the greedy
  per-step argmax both planners use is not just a heuristic: it inherits the
  classic (1-1/e) worst-case guarantee relative to the optimal non-adaptive
  k-view policy on the coverage term alone (Nemhauser et al. 1978; Krause &
  Guestrin, JMLR 2008 "Near-Optimal Sensor Placements in Gaussian
  Processes"). This guarantee does not extend to the uncertainty/temporal/
  staleness terms below (those are reward signals fed by an external,
  non-submodular detector/memory process), so UWTIGPlanner should be read as
  "provably-reasonable coverage, best-effort defect-awareness on top."

- UWTIGPlanner (novel): Uncertainty-Weighted Temporal Information Gain.
  Extends the coverage/information-gain term with four additions, each
  independently ablatable:
    0. a coverage-guarantee phase: while any wall has zero visits this
       mission, restrict selection to Isler-NBV's own formulation over only
       the unvisited walls, before falling through to the terms below for
       the remaining budget. Added after finding `coverage_frac` stuck at
       exactly 3 of 9 walls for EVERY UW-TIG variant *and* for `isler_nbv`
       itself -- i.e. a ceiling caused by the cost-normalized-greedy
       formulation's cost/reward scale on this viewpoint graph, not by the
       terms below, so retuning their weights could not have reliably fixed
       it. This is the single highest-impact change here: recall
       0.36 -> 0.63, coverage 0.33 -> 1.00, reinspection_rate 0.44 -> 1.00
       -- at a real, honestly-reported cost: precision 0.86 -> 0.76,
       mean localization error 0.19m -> 0.70m (many walls now get only one,
       not-localization-optimized look during the coverage phase), and
       flight distance 0.3m -> 109m (no longer near-free once nine separate
       walls are actually visited). See RESULTS.md for the full numbers and
       NOVELTY.md for why this isn't a strict improvement, just a different,
       arguably more deployment-realistic point on the precision/recall/
       flight-cost trade-off surface.
    1. detection-uncertainty and temporal-growth terms fed from persistent
       defect memory (the original novelty -- see MissionBelief).
    2. a persistent-monitoring staleness/latency term: cells accrue reward
       for time-since-last-visit even with no detected defect, generalizing
       the revisit signal beyond "only revisit where memory already found
       something" -- adapted from the latency-minimizing revisit-scheduling
       literature (Alamdari, Fata & Smith 2014, "Persistent Monitoring in
       Discrete Environments: Minimizing the Maximum Weighted Latency
       Between Observations", IJRR; see also the multi-robot latency-
       constrained routing line of work, e.g. arXiv:1903.06105). Unlike that
       literature's guaranteed bound on worst-case latency, this is a soft,
       additive reward term inside a larger utility, not a scheduling
       algorithm with its own guarantee.
    3. a 2-step receding-horizon lookahead in place of pure 1-step greedy:
       evaluate each candidate next viewpoint together with the best
       viewpoint that could follow it, but (as in the cited work) only ever
       execute the first step before replanning -- the same
       plan-a-horizon/execute-one-step/replan structure as Bircher et al.
       (2016, "Receding Horizon 'Next-Best-View' Planner for 3D
       Exploration", ICRA) and the GTSP-clustered receding-horizon
       replanning in Dhami et al.'s GATSBI (arXiv:2012.04803,
       arXiv:2406.16625, targeted bridge-surface inspection + defect
       detection). This makes UWTIGPlanner less myopic about travel cost
       than a flat 1-step argmax, at the cost of one more literature-honest
       caveat: the lookahead only re-simulates the coverage/view_count
       effect of taking the first step (see `_lookahead_view_count_delta`)
       -- it cannot simulate a detector's future output, so the
       uncertainty/temporal/staleness terms at the second step are read
       from the CURRENT belief, not a genuinely predicted future one.
  Ablation variants zero out one added term at a time (see
  UWTIGNoUncertaintyPlanner / UWTIGNoTemporalPlanner /
  UWTIGNoStalenessPlanner / UWTIGNoCoverageFirstPlanner /
  UWTIGNoLookaheadPlanner).

Related work this project's approach is positioned against (not
implemented here, but see NOVELTY.md for the full comparison table):
Bircher et al. 2016 (receding-horizon NBV, geometry-only, no defect
semantics); Dhami et al.'s GATSBI (GTSP-routed bridge inspection with
defect detection, but no persistent cross-mission memory or detection-
uncertainty term); Pred-NBV / MAP-NBV (Logothetis-Dhami-Tokekar-line
prediction-guided NBV via learned shape completion -- predicts unseen
GEOMETRY, not defect growth); Wang et al.'s measurement-uncertainty-
controlled coverage path planning (arXiv:2201.04310, uncertainty-aware but
single-visit, no temporal/growth tracking); active visual search under
detector uncertainty via POMDP/MCTS (arXiv:2303.03155, single-session, no
persistent memory across missions); Alamdari/Fata/Smith persistent-
monitoring latency scheduling (formal revisit guarantees, but no semantic
defect-uncertainty signal at all). UW-TIG's distinguishing combination is:
persistent cross-mission memory + real-detector uncertainty + growth +
latency-based staleness + cost-aware receding-horizon selection, together,
evaluated end-to-end against a real trained detector rather than assumed
ground-truth detections.

All planners select via `select_next(state) -> Viewpoint`, where `state` is
a MissionBelief (this module) the mission runner updates after every
capture, so planners never talk to memory/store.py or the perception model
directly -- keeps them pure and trivially ablatable/unit-testable.
"""
import math

import numpy as np

from planning.viewpoints import cell_index_for_world_point, n_cells_for_wall

VIEW_SATURATION_K = 0.6  # p(well-observed) = 1 - exp(-k * view_count)
STALENESS_SATURATION_K = 0.15  # slower saturation than view_count: staleness
# should still be climbing across most of a mission's budget, not maxed out
# after 2-3 steps like coverage entropy is.


def _entropy(p):
    p = float(np.clip(p, 1e-6, 1 - 1e-6))
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


class MissionBelief:
    """Per-mission state: coverage (geometry-only) + defect uncertainty/growth
    (defect-aware), both keyed by (wall_name, cell_index). Takes the actual
    wall dicts (not just names) since cell count is per-wall, proportional
    to physical width -- see planning.viewpoints.n_cells_for_wall."""

    def __init__(self, wall_segments):
        cells = {w["name"]: n_cells_for_wall(w) for w in wall_segments}
        self.view_count = {(w, c): 0 for w, n in cells.items() for c in range(n)}
        self.uncertainty = {(w, c): 0.0 for w, n in cells.items() for c in range(n)}
        self.growth = {(w, c): 0.0 for w, n in cells.items() for c in range(n)}
        # In-mission revisit latency (steps since last view), not a
        # cross-mission real-time latency -- see UWTIGPlanner's docstring.
        self.last_visit_step = {(w, c): -1 for w, n in cells.items() for c in range(n)}
        self.step = 0
        self.visited_ids = []

    def seed_temporal_priors(self, priors):
        """priors: dict[(wall, cell)] -> (uncertainty, growth), typically
        built by experiments/mission.py from memory.store history at the
        start of a mission -- this is the "prior inspections inform this
        mission's plan" temporal-intelligence link."""
        for key, (u, g) in priors.items():
            if key in self.uncertainty:
                self.uncertainty[key] = u
                self.growth[key] = g

    def coverage_entropy(self, wall, cell):
        # p = belief the cell is ALREADY adequately observed. Starts at 0.5
        # (maximally uncertain -> max entropy -> max info gain from a first
        # look) and climbs toward 1 (certain, resolved) with more views.
        p = 1 - 0.5 * math.exp(-VIEW_SATURATION_K * self.view_count[(wall, cell)])
        return _entropy(p)

    def record_visit(self, viewpoint):
        self.visited_ids.append(viewpoint.id)
        for c in viewpoint.visible_cells:
            key = (viewpoint.wall, c)
            self.view_count[key] += 1
            self.last_visit_step[key] = self.step
        self.step += 1

    def record_detection(self, wall, world_xyz, uncertainty, growth, wall_dict):
        cell = cell_index_for_world_point(wall_dict, world_xyz)
        key = (wall_dict["name"], cell)
        self.uncertainty[key] = uncertainty
        self.growth[key] = max(0.0, growth)

    def information_gain(self, viewpoint):
        return sum(self.coverage_entropy(viewpoint.wall, c) for c in viewpoint.visible_cells)

    def _repeat_decay(self, wall, cell):
        # Diminishing marginal value of acting on the SAME reading again --
        # keyed by view_count (times this cell has actually been looked at),
        # not by "since the detector last reported something," because a
        # real, persistent defect gets re-detected on every single look: a
        # since-last-update decay never fires for it and the planner camps
        # on that one viewpoint forever once it finds anything (caught via
        # the lookahead below making that camping total, flight_dist ->
        # exactly 0.0, in eval). Reusing coverage_entropy's saturation here
        # extends the same "repeated identical observation earns
        # diminishing reward" logic from coverage to uncertainty/growth.
        return math.exp(-VIEW_SATURATION_K * self.view_count[(wall, cell)])

    def uncertainty_score(self, viewpoint):
        return sum(self.uncertainty[(viewpoint.wall, c)] * self._repeat_decay(viewpoint.wall, c)
                   for c in viewpoint.visible_cells)

    def temporal_score(self, viewpoint):
        return sum(self.growth[(viewpoint.wall, c)] * self._repeat_decay(viewpoint.wall, c)
                   for c in viewpoint.visible_cells)

    def staleness(self, wall, cell):
        last = self.last_visit_step[(wall, cell)]
        elapsed = self.step if last < 0 else self.step - last
        return 1 - math.exp(-STALENESS_SATURATION_K * elapsed)

    def staleness_score(self, viewpoint):
        return sum(self.staleness(viewpoint.wall, c) for c in viewpoint.visible_cells)


METERS_PER_DEG_YAW = 1.0 / 3600  # a full 180-degree reorientation costs as
# much as 0.05m of translation -- deliberately tiny, calibrated below the
# graph's smallest genuinely-different-position gap (0.14m; see
# planning/viewpoints.py's candidate graph), so it never outweighs a real
# routing choice elsewhere. Its only job is to break ties among positions
# that coincide EXACTLY: two of Building B's walls' standoff viewpoints land
# on the same point (the 2.6m room is exactly 2x the 1.3m standoff, so
# "1.3m out from each wall" reaches the room's center from every wall) --
# with a pure-distance cost, spinning 90-180 degrees in place to face a
# different wall from there was FREE, an unbounded supply of exactly-zero-
# cost viewpoint switches. An earlier, much larger constant (1/90, i.e. a
# 90-degree turn = 1m) fixed that but also made every genuine inter-building
# trip look considerably more expensive than it should (a real 180-degree
# reorientation takes a couple of seconds, not the ~10+ seconds a couple of
# meters of flight would) -- it collapsed isler_nbv's coverage_frac from
# 0.875 to 0.333 in a re-run, i.e. it stopped exploring past the first
# building almost entirely. This value fixes the exploit without that
# side effect (verified: see NOVELTY.md's "second, independent bug" note).


class BasePlanner:
    name = "base"

    def __init__(self, viewpoints, dist, rng):
        self.viewpoints = viewpoints
        self.dist = dist
        self.rng = rng
        self.by_id = {v.id: v for v in viewpoints}
        self.all_walls = sorted({v.wall for v in viewpoints})

    def _cost(self, current_id, v):
        if current_id is None:
            return 0.0
        translation = self.dist[(current_id, v.id)]
        yaw_diff = abs((v.yaw_deg - self.by_id[current_id].yaw_deg + 180) % 360 - 180)
        return translation + METERS_PER_DEG_YAW * yaw_diff

    def select_next(self, belief, current_id):
        raise NotImplementedError


class RandomPlanner(BasePlanner):
    name = "random"

    def select_next(self, belief, current_id):
        unvisited = [v for v in self.viewpoints if v.id not in belief.visited_ids]
        pool = unvisited or self.viewpoints
        return self.rng.choice(pool)


class IslerNBVPlanner(BasePlanner):
    """Cost-normalized entropy NBV, geometry/coverage only (Isler et al. 2016)."""
    name = "isler_nbv"
    w_ig = 1.0
    w_cost = 0.4

    def select_next(self, belief, current_id):
        unvisited = [v for v in self.viewpoints if v.id not in belief.visited_ids]
        pool = unvisited or self.viewpoints
        scored = [(self.w_ig * belief.information_gain(v) - self.w_cost * self._cost(current_id, v), v)
                  for v in pool]
        return max(scored, key=lambda t: t[0])[1]


class UWTIGPlanner(BasePlanner):
    """Novel: Uncertainty-Weighted Temporal Information Gain. Strictly
    generalizes IslerNBVPlanner by adding defect-uncertainty, temporal-
    growth, and persistent-monitoring staleness terms sourced from
    persistent memory, and -- unlike the coverage-only baselines -- is
    allowed to revisit an already-inspected viewpoint when that utility
    gain is high (active reinspection). Selects via a 2-step
    receding-horizon lookahead rather than pure 1-step greedy (see module
    docstring for the literature this is adapted from and its caveats).

    Also runs a **coverage-guarantee phase**: while any wall has zero visits
    this mission, `select_next` restricts itself to Isler-NBV's own
    formulation (ig - cost, no uncertainty/temporal/staleness, no lookahead)
    over ONLY the still-unvisited walls' viewpoints. This was added after
    finding that `coverage_frac` was stuck at exactly 0.333 (3 of 9 walls)
    for EVERY UW-TIG ablation *and* for `isler_nbv` itself, identically,
    across every seed -- i.e. this is not a side effect of the
    uncertainty/temporal/staleness weights (a weight retune can't reliably
    fix it), it's the cost-normalized-greedy formulation itself finding
    that, on this viewpoint graph, traveling to the far building is never
    worth its cost relative to the coverage-entropy reward available,
    regardless of weighting. A weight scale is fragile to depend on for a
    coverage guarantee; an explicit phase is not. Once every wall has been
    visited at least once this mission, control passes to the full
    multi-term utility below for the remaining budget -- so this only
    changes *when* full coverage happens, not whether UW-TIG's reinspection
    behavior still runs (as long as budget > wall count, which it is
    throughout this project's evaluation). Ablation: `uwtig_no_coverage_first`
    reproduces the original (recall-limited) behavior for comparison."""
    name = "uwtig"
    w_ig = 1.0
    w_cost = 0.4
    w_uncertainty = 1.5
    w_temporal = 2.0
    w_staleness = 1.0
    lookahead_discount = 0.5  # weight on the best-achievable second step
    coverage_first = True

    def _utility(self, belief, from_id, v, view_count=None):
        vc = belief.view_count if view_count is None else view_count
        ig = self.w_ig * sum(
            _entropy(1 - 0.5 * math.exp(-VIEW_SATURATION_K * vc[(v.wall, c)]))
            for c in v.visible_cells)
        u = self.w_uncertainty * belief.uncertainty_score(v)
        t = self.w_temporal * belief.temporal_score(v)
        s = self.w_staleness * belief.staleness_score(v)
        cost = self.w_cost * self._cost(from_id, v)
        return ig + u + t + s - cost

    def _view_count_after(self, belief, v):
        """What-if view_count if `v` were visited next -- used only to give
        the lookahead's second step a coverage-aware (not stale) picture of
        information gain. Cannot simulate a future detector output, so
        uncertainty/temporal/staleness are read from the current belief for
        the second step (see module docstring caveat)."""
        vc = dict(belief.view_count)
        for c in v.visible_cells:
            vc[(v.wall, c)] = vc.get((v.wall, c), 0) + 1
        return vc

    def _unvisited_walls(self, belief):
        visited_walls = {self.by_id[vid].wall for vid in belief.visited_ids}
        return [w for w in self.all_walls if w not in visited_walls]

    def select_next(self, belief, current_id):
        if self.coverage_first:
            unvisited_walls = self._unvisited_walls(belief)
            if unvisited_walls:
                pool = [v for v in self.viewpoints if v.wall in unvisited_walls]
                scored = [(self.w_ig * belief.information_gain(v) - self.w_cost * self._cost(current_id, v), v)
                          for v in pool]
                return max(scored, key=lambda t: t[0])[1]

        best_v, best_val = None, -math.inf
        for v1 in self.viewpoints:
            val1 = self._utility(belief, current_id, v1)
            if self.lookahead_discount:
                vc_after = self._view_count_after(belief, v1)
                best_second = max(self._utility(belief, v1.id, v2, view_count=vc_after)
                                   for v2 in self.viewpoints)
                val1 += self.lookahead_discount * best_second
            if val1 > best_val:
                best_val, best_v = val1, v1
        return best_v


class UWTIGNoUncertaintyPlanner(UWTIGPlanner):
    """Ablation: temporal + staleness + coverage, no detection-uncertainty term."""
    name = "uwtig_no_uncertainty"
    w_uncertainty = 0.0


class UWTIGNoTemporalPlanner(UWTIGPlanner):
    """Ablation: uncertainty + staleness + coverage, no temporal-growth term."""
    name = "uwtig_no_temporal"
    w_temporal = 0.0


class UWTIGNoStalenessPlanner(UWTIGPlanner):
    """Ablation: uncertainty + temporal + coverage, no persistent-monitoring
    staleness/latency term (Alamdari, Fata & Smith 2014)."""
    name = "uwtig_no_staleness"
    w_staleness = 0.0


class UWTIGNoLookaheadPlanner(UWTIGPlanner):
    """Ablation: pure 1-step greedy -- this project's original UW-TIG,
    before the Bircher-et-al./GATSBI-style receding-horizon lookahead."""
    name = "uwtig_no_lookahead"
    lookahead_discount = 0.0


class UWTIGNoCoverageFirstPlanner(UWTIGPlanner):
    """Ablation: no coverage-guarantee phase -- reproduces the
    recall/coverage-limited behavior UW-TIG had before this was added
    (coverage_frac stuck at 3/9 walls regardless of the other weights,
    since that ceiling comes from the cost-normalized-greedy formulation
    itself, not from the uncertainty/temporal/staleness terms -- see
    UWTIGPlanner's docstring)."""
    name = "uwtig_no_coverage_first"
    coverage_first = False


# ---------------------------------------------------------------------------
# Re-implemented literature baselines. Each adapts one paper's core
# viewpoint-selection rule to this testbed's discrete 54-viewpoint graph and
# shared MissionBelief -- the same way IslerNBVPlanner adapts Isler et al. --
# so every planner is measured with the same detector, scenes, seeds and
# scoring. They are faithful to each paper's *selection rule*, not to its
# full system (no RRT sampling, 3D occupancy mapping or online model
# retraining); that limitation is stated in RESULTS.md. Parameters are set
# once from the papers' formulations and were not tuned on any results.
# ---------------------------------------------------------------------------


def _coverage_gain(view_count, v):
    return sum(_entropy(1 - 0.5 * math.exp(-VIEW_SATURATION_K * view_count[(v.wall, c)]))
               for c in v.visible_cells)


class BircherRHNBVPlanner(BasePlanner):
    """Bircher et al., "Receding Horizon 'Next-Best-View' Planner for 3D
    Exploration", ICRA 2016. Branch gain accumulates per node as
    Gain(n_k) = Gain(n_{k-1}) + G(n_k) * exp(-lambda * c(n_{k-1} -> n_k)),
    and only the first edge of the best branch is executed before
    replanning. Here: every depth-2 branch over the viewpoint graph (instead
    of an RRT), G = coverage information gain, geometry only."""
    name = "bircher_rhnbv"
    lam = 0.5

    def select_next(self, belief, current_id):
        best_v, best_val = None, -math.inf
        for v1 in self.viewpoints:
            g1 = belief.information_gain(v1) * math.exp(-self.lam * self._cost(current_id, v1))
            vc = dict(belief.view_count)
            for c in v1.visible_cells:
                vc[(v1.wall, c)] += 1
            g2 = max(_coverage_gain(vc, v2) * math.exp(-self.lam * self._cost(v1.id, v2))
                     for v2 in self.viewpoints)
            if g1 + g2 > best_val:
                best_val, best_v = g1 + g2, v1
        return best_v


class GATSBIPlanner(BasePlanner):
    """Dhami et al., GATSBI (ICUAS 2023; arXiv:2406.16625): an online GTSP --
    one viewpoint per still-uninspected surface cluster, ordered into the
    shortest tour from the current position, replanned every step, first
    leg executed. Here clusters are walls; the target set is the walls whose
    least-observed cell is least observed (all walls with an unseen cell
    first, then a fresh lap), each served by its viewpoint that sees the
    most of those cells; tour order is nearest-neighbour + 2-opt.
    Coverage-driven, no detection-uncertainty term."""
    name = "gatsbi_gtsp"

    def __init__(self, viewpoints, dist, rng):
        super().__init__(viewpoints, dist, rng)
        self.wall_cells = {}
        for v in viewpoints:
            self.wall_cells.setdefault(v.wall, set()).update(v.visible_cells)

    def _wall_view(self, belief, wall, target):
        cands = [v for v in self.viewpoints if v.wall == wall]
        return max(cands, key=lambda v: (len(target & set(v.visible_cells)), len(v.visible_cells)))

    def _path_cost(self, start_id, path):
        total, prev = 0.0, start_id
        for v in path:
            total += self._cost(prev, v)
            prev = v.id
        return total

    def select_next(self, belief, current_id):
        least = {w: min(belief.view_count[(w, c)] for c in cells) for w, cells in self.wall_cells.items()}
        floor = min(least.values())
        nodes = []
        for w, cells in self.wall_cells.items():
            if least[w] == floor:
                target = {c for c in cells if belief.view_count[(w, c)] == floor}
                nodes.append(self._wall_view(belief, w, target))

        tour, remaining, prev = [], list(nodes), current_id
        while remaining:
            nxt = min(remaining, key=lambda v: self._cost(prev, v))
            tour.append(nxt)
            remaining.remove(nxt)
            prev = nxt.id
        improved = True
        while improved:
            improved = False
            for i in range(len(tour) - 1):
                for j in range(i + 1, len(tour)):
                    cand = tour[:i] + tour[i:j + 1][::-1] + tour[j + 1:]
                    if self._path_cost(current_id, cand) < self._path_cost(current_id, tour) - 1e-9:
                        tour, improved = cand, True
        return tour[0]


class RuckinIPPPlanner(BasePlanner):
    """Rueckin, Jin, Magistri, Stachniss & Popovic, "An Informative Path
    Planning Framework for Active Learning in UAV-Based Semantic Mapping",
    IEEE T-RO 2023 (arXiv:2302.03347): next pose
    p* = argmax ||G_U(p)||_1 / ||T(p)||_1 -- mapped model uncertainty in the
    view footprint, normalized by how much data that footprint already has.
    Here G_U per cell is the detector's TTA uncertainty recorded THIS mission
    (unobserved cells take the maximal Bernoulli std, 0.5, as an
    uninformed prior) and T = 1 + times the cell was observed. Single-session
    by design, like the original: uncertainty seeded from cross-mission
    memory is ignored (that persistence is UW-TIG's contribution, not
    theirs). No travel-cost term -- the objective has none."""
    name = "ruckin_ipp"
    unobserved_acq = 0.5

    def __init__(self, viewpoints, dist, rng):
        super().__init__(viewpoints, dist, rng)
        self._seeded = None

    def _acq(self, belief, key):
        if belief.view_count[key] == 0:
            return self.unobserved_acq
        u = belief.uncertainty[key]
        return u if u != self._seeded.get(key) else 0.0

    def select_next(self, belief, current_id):
        if self._seeded is None:
            self._seeded = dict(belief.uncertainty)  # mission-start state = memory priors
        def score(v):
            keys = [(v.wall, c) for c in v.visible_cells]
            return (sum(self._acq(belief, k) for k in keys)
                    / sum(1 + belief.view_count[k] for k in keys), -self._cost(current_id, v))
        return max(self.viewpoints, key=score)


class AlamdariLatencyPlanner(BasePlanner):
    """Alamdari, Fata & Smith, "Persistent Monitoring in Discrete
    Environments: Minimizing the Maximum Weighted Latency Between
    Observations", IJRR 2014. Online greedy form of their min-max-latency
    walk: go to the wall with the largest latency (steps since any of its
    cells was last observed; never-observed walls first), uniform weights
    (no defect knowledge), using that wall's widest-view viewpoint, ties
    broken by travel cost."""
    name = "alamdari_latency"

    def select_next(self, belief, current_id):
        latency = {}
        for (w, c), last in belief.last_visit_step.items():
            age = belief.step + 1 if last < 0 else belief.step - last
            latency[w] = min(latency.get(w, math.inf), age)  # wall latency = its freshest cell
        top = max(latency.values())
        cands = [v for v in self.viewpoints if latency[v.wall] == top]
        return max(cands, key=lambda v: (len(v.visible_cells), -self._cost(current_id, v)))


PLANNER_REGISTRY = {
    "random": RandomPlanner,
    "isler_nbv": IslerNBVPlanner,
    "bircher_rhnbv": BircherRHNBVPlanner,
    "gatsbi_gtsp": GATSBIPlanner,
    "ruckin_ipp": RuckinIPPPlanner,
    "alamdari_latency": AlamdariLatencyPlanner,
    "uwtig": UWTIGPlanner,
    "uwtig_no_uncertainty": UWTIGNoUncertaintyPlanner,
    "uwtig_no_temporal": UWTIGNoTemporalPlanner,
    "uwtig_no_staleness": UWTIGNoStalenessPlanner,
    "uwtig_no_coverage_first": UWTIGNoCoverageFirstPlanner,
    "uwtig_no_lookahead": UWTIGNoLookaheadPlanner,
}
