"""Scenario generators for the planner comparison (proposal's Verification
Method: static / uncertain / growing / multiple defects). Each scenario
assigns wall textures for a given mission index and returns ground truth
(defect class, severity, pixel-space center used only for reproducing the
same physical spot mission-to-mission) for scoring.

The static/uncertain/multi_defect scenarios use real MBDD2025 photos
(datagen/mbdd_textures.py) as the wall texture itself -- genuine defect
appearance. "growing" uses the procedural generator (scene/texture_gen.py)
instead, since a single-timepoint photo dataset has no repeated-visit
growth sequence for the same physical defect.
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datagen import mbdd_textures  # noqa: E402
from scene import texture_gen  # noqa: E402

CLEAN_WALLS_ALWAYS = True  # walls with no assigned defect stay "clean" every mission


class Scenario:
    name = "base"
    provider = texture_gen  # module exposing make_wall_texture(...); override per scenario

    def __init__(self, seed):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self._centers = {}  # wall -> pixel center, fixed across missions once first drawn
        self._base_colors = {}
        self.assignment = self._build_assignment()

    def _build_assignment(self):
        """Returns {wall_name: defect_type} for walls that carry a defect
        this scenario; walls not listed are rendered clean."""
        raise NotImplementedError

    def severity_for(self, mission_index):
        raise NotImplementedError

    def ground_truth(self, mission_index):
        """{wall_name: {"defect_type":..., "severity":...}} for this mission."""
        sev = self.severity_for(mission_index)
        return {wall: {"defect_type": dtype, "severity": sev} for wall, dtype in self.assignment.items()}

    def setup_mission(self, house, mission_index, tmp_dir):
        gt = self.ground_truth(mission_index)
        for wall_name in house.wall_by_name:
            dtype = "clean"
            severity = 0.0
            if wall_name in gt:
                dtype = gt[wall_name]["defect_type"]
                severity = gt[wall_name]["severity"]

            center = self._centers.get(wall_name)
            base_color = self._base_colors.get(wall_name)
            tex, _, meta = self.provider.make_wall_texture(
                dtype, self.rng, severity=max(severity, 0.01) if dtype != "clean" else 0.0,
                base_color=base_color, center=center)
            self._centers.setdefault(wall_name, meta["center"])
            self._base_colors.setdefault(wall_name, meta["base_color"])

            path = os.path.join(tmp_dir, f"{wall_name}_{mission_index}.png")
            tex.save(path)
            house.set_wall_texture(wall_name, path)
        return gt


class StaticScenario(Scenario):
    """A few walls carry fixed-severity, unchanging defects across missions
    -- steady-state detection/coverage, no temporal signal expected."""
    name = "static"
    provider = mbdd_textures

    def _build_assignment(self):
        return {"A-west": "crack", "A-east": "corrosion", "B-north": "leakage"}

    def severity_for(self, mission_index):
        return 1.0


class UncertainScenario(Scenario):
    """Low-severity, ambiguous defects -- meant to produce low-confidence,
    high-variance detections that only the uncertainty-driven planner
    should prioritize revisiting."""
    name = "uncertain"
    provider = mbdd_textures

    def _build_assignment(self):
        return {"A-south": "crack", "B-east": "corrosion"}

    def severity_for(self, mission_index):
        return 0.35


class GrowingScenario(Scenario):
    """One defect at a fixed location grows across sequential missions --
    procedural-only (see module docstring): ground truth growth rate is
    exactly known, for scoring temporal-memory growth-detection accuracy."""
    name = "growing"

    def _build_assignment(self):
        return {"A-east": "corrosion"}

    def severity_for(self, mission_index):
        return min(1.3, 0.4 + 0.3 * (mission_index - 1))


class MultiDefectScenario(Scenario):
    """Many concurrent defects of different classes across both rooms --
    stresses coverage breadth vs. reinspection-depth tradeoffs."""
    name = "multi_defect"
    provider = mbdd_textures

    def _build_assignment(self):
        return {
            "A-west": "crack", "A-east": "corrosion", "A-south": "leakage",
            "B-west": "crack", "B-east": "corrosion", "B-north": "leakage",
        }

    def severity_for(self, mission_index):
        return 0.9


SCENARIO_REGISTRY = {
    "static": StaticScenario,
    "uncertain": UncertainScenario,
    "growing": GrowingScenario,
    "multi_defect": MultiDefectScenario,
}


if __name__ == "__main__":
    from experiments.kinematic_capture import KinematicHouse

    house = KinematicHouse()
    with tempfile.TemporaryDirectory() as td:
        for name, cls in SCENARIO_REGISTRY.items():
            scen = cls(seed=0)
            for mission_index in (1, 2, 3):
                gt = scen.setup_mission(house, mission_index, td)
                print(name, "mission", mission_index, "->", gt)
    house.close()
