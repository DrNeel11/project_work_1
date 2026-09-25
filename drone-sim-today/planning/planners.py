"""Three planners compared by experiments/evaluate.py, sharing one candidate
viewpoint graph (planning/viewpoints.py):

- RandomPlanner: uniform random choice among not-yet-visited viewpoints.
  The naive baseline the proposal's Verification Method calls for.

- IslerNBVPlanner: cost-normalized entropy-based next-best-view, adapted
  from Isler et al. (2016)'s volumetric information-gain formulation to this
  2D wall-surface setting (a coarse per-wall coverage grid replaces the
  voxel grid; entropy is over a "surface adequately observed" belief, not
  occupancy). Deliberately geometry/coverage-only, no defect semantics --
  this is the literature gap the proposal identifies for this base paper.

- UWTIGPlanner (novel): the same coverage/information-gain term, PLUS
  detection-uncertainty and temporal-growth terms fed from persistent
  defect memory, combined in one weighted utility (Uncertainty-Weighted
  Temporal Information Gain). Ablation variants zero out one added term.

All three select via `select_next(state) -> Viewpoint`, where `state` is a
MissionBelief (this module) the mission runner updates after every capture,
so planners never talk to memory/store.py or the perception model directly
-- keeps them pure and trivially ablatable/unit-testable.
"""
import math

import numpy as np

from planning.viewpoints import N_CELLS, cell_index_for_world_point

VIEW_SATURATION_K = 0.6  # p(well-observed) = 1 - exp(-k * view_count)


def _entropy(p):
    p = float(np.clip(p, 1e-6, 1 - 1e-6))
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


class MissionBelief:
    """Per-mission state: coverage (geometry-only) + defect uncertainty/growth
    (defect-aware), both keyed by (wall_name, cell_index)."""

    def __init__(self, wall_names):
        self.view_count = {(w, c): 0 for w in wall_names for c in range(N_CELLS)}
        self.uncertainty = {(w, c): 0.0 for w in wall_names for c in range(N_CELLS)}
        self.growth = {(w, c): 0.0 for w in wall_names for c in range(N_CELLS)}
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
            self.view_count[(viewpoint.wall, c)] += 1

    def record_detection(self, wall, world_xyz, uncertainty, growth, wall_dict):
        cell = cell_index_for_world_point(wall_dict, world_xyz)
        self.uncertainty[(wall_dict["name"], cell)] = uncertainty
        self.growth[(wall_dict["name"], cell)] = max(0.0, growth)

    def information_gain(self, viewpoint):
        return sum(self.coverage_entropy(viewpoint.wall, c) for c in viewpoint.visible_cells)

    def uncertainty_score(self, viewpoint):
        return sum(self.uncertainty[(viewpoint.wall, c)] for c in viewpoint.visible_cells)

    def temporal_score(self, viewpoint):
        return sum(self.growth[(viewpoint.wall, c)] for c in viewpoint.visible_cells)


class BasePlanner:
    name = "base"

    def __init__(self, viewpoints, dist, rng):
        self.viewpoints = viewpoints
        self.dist = dist
        self.rng = rng

    def _cost(self, current_id, v):
        if current_id is None:
            return 0.0
        return self.dist[(current_id, v.id)]

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
    generalizes IslerNBVPlanner by adding defect-uncertainty and
    temporal-growth terms sourced from persistent memory, and -- unlike the
    coverage-only baselines -- is allowed to revisit an already-inspected
    viewpoint when that utility gain is high (active reinspection)."""
    name = "uwtig"
    w_ig = 1.0
    w_cost = 0.4
    w_uncertainty = 1.5
    w_temporal = 2.0

    def select_next(self, belief, current_id):
        scored = []
        for v in self.viewpoints:
            u = self.w_uncertainty * belief.uncertainty_score(v)
            t = self.w_temporal * belief.temporal_score(v)
            ig = self.w_ig * belief.information_gain(v)
            cost = self.w_cost * self._cost(current_id, v)
            scored.append((ig + u + t - cost, v))
        return max(scored, key=lambda t: t[0])[1]


class UWTIGNoUncertaintyPlanner(UWTIGPlanner):
    """Ablation: temporal + coverage, no detection-uncertainty term."""
    name = "uwtig_no_uncertainty"
    w_uncertainty = 0.0


class UWTIGNoTemporalPlanner(UWTIGPlanner):
    """Ablation: uncertainty + coverage, no temporal-growth term."""
    name = "uwtig_no_temporal"
    w_temporal = 0.0


PLANNER_REGISTRY = {
    "random": RandomPlanner,
    "isler_nbv": IslerNBVPlanner,
    "uwtig": UWTIGPlanner,
    "uwtig_no_uncertainty": UWTIGNoUncertaintyPlanner,
    "uwtig_no_temporal": UWTIGNoTemporalPlanner,
}
