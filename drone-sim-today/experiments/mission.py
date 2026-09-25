"""Runs one planner x scenario x seed x mission-sequence, wiring together:
planning.viewpoints/planners (where to look), a pluggable detector
(perception.ml_detector, class+confidence+uncertainty per detection),
geometry.py (2D detection -> 3D world position), and memory.store
(persistent cross-mission defect identity + growth). Emits a per-step log
consumed by experiments/evaluate.py for metrics.

A detector is any callable: bgr_frame -> list of
{"bbox": (x,y,w,h), "label": str, "confidence": float, "uncertainty": float}.
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geometry as geo  # noqa: E402
from experiments.kinematic_capture import KinematicHouse  # noqa: E402
from planning.planners import PLANNER_REGISTRY, MissionBelief  # noqa: E402
from planning.viewpoints import N_CELLS, build_viewpoints, cell_index_for_world_point  # noqa: E402
from sim_house import WALL_SEGMENTS  # noqa: E402

IMG_W, IMG_H = 320, 240


def _seed_priors_from_memory(mem, wall_names, run_key):
    """Builds {(wall, cell): (uncertainty, growth)} from each wall's active
    defect history -- the link from persistent memory into a NEW mission's
    plan (temporal defect intelligence). Scoped to `run_key` (this
    scenario+planner+seed's own namespaced wall keys, see run_mission) so
    comparing planners on the same seeded scenario never leaks one
    planner's detection history into another's belief -- each hypothetical
    deployment gets its own memory, same as a real one would."""
    priors = {}
    for wall in wall_names:
        wall_dict = next(w for w in WALL_SEGMENTS if w["name"] == wall)
        wall_key = f"{run_key}::{wall}"
        for d in mem.active_defects_on_wall(wall_key):
            history = mem.get_defect_history(d["id"])
            if not history:
                continue
            last = history[-1]
            cell = cell_index_for_world_point(wall_dict, (d["world_x"], d["world_y"], d["world_z"]))
            growth = mem.compute_growth(d["id"])
            priors[(wall, cell)] = (last["uncertainty"], max(0.0, growth))
    return priors


def run_mission(planner_name, scenario, mission_index, detector, mem, rng,
                 budget=10, gui=False, seed=0):
    """One mission: `scenario` must already have `assignment`/ground truth
    ready (see experiments/scenarios.py); ground truth for THIS mission
    index is scenario.ground_truth(mission_index). Returns a dict log.

    `seed` identifies this scenario+planner+seed run for memory isolation
    (see _seed_priors_from_memory) -- pass the actual experiment seed, not
    a fresh random draw, so all mission_index calls in the same run share
    one namespace and different (planner, seed) runs never collide."""
    wall_names = [w["name"] for w in WALL_SEGMENTS]
    run_key = f"{scenario.name}|{planner_name}|{seed}"
    viewpoints, dist = build_viewpoints(WALL_SEGMENTS)
    planner = PLANNER_REGISTRY[planner_name](viewpoints, dist, rng)
    belief = MissionBelief(wall_names)

    mission_id = mem.create_mission(scenario.name, planner_name, seed, mission_index)
    if mission_index > 1:
        belief.seed_temporal_priors(_seed_priors_from_memory(mem, wall_names, run_key))

    house = KinematicHouse(gui=gui)
    with tempfile.TemporaryDirectory() as tmp_dir:
        gt = scenario.setup_mission(house, mission_index, tmp_dir)

        steps = []
        current_id = None
        total_dist = 0.0
        wall_detections = {w: [] for w in wall_names}

        for step_i in range(budget):
            vp = planner.select_next(belief, current_id)
            cost = dist[(current_id, vp.id)] if current_id else 0.0
            total_dist += cost

            bgr, pos, quat = house.capture(vp)
            wall_dict = house.wall_by_name[vp.wall]
            dets = detector(bgr)

            step_record = {"step": step_i, "viewpoint": vp.id, "wall": vp.wall,
                           "cost": cost, "cum_dist": total_dist, "detections": []}
            for det in dets:
                x, y, w, h = det["bbox"]
                center_px = (x + w / 2, y + h / 2)
                world_xyz = geo.localize_on_wall(center_px, pos, quat, wall_dict, IMG_W, IMG_H)
                if world_xyz is None:
                    continue
                corners = [geo.localize_on_wall((x, y), pos, quat, wall_dict, IMG_W, IMG_H),
                           geo.localize_on_wall((x + w, y + h), pos, quat, wall_dict, IMG_W, IMG_H)]
                corners = [c for c in corners if c is not None]
                size_m = float(np.linalg.norm(corners[0] - corners[1])) if len(corners) == 2 else 0.0

                crop = bgr[max(0, y):y + h, max(0, x):x + w]
                wall_key = f"{run_key}::{vp.wall}"
                det_id, defect_id, is_new, growth = mem.match_or_create_defect(
                    mission_id, wall_key, det["label"], det["confidence"], det["uncertainty"],
                    (x, y, w, h), tuple(world_xyz), size_m, crop_bgr=crop)

                belief.record_detection(vp.wall, world_xyz, det["uncertainty"], growth, wall_dict)
                wall_detections[vp.wall].append(det["label"])
                step_record["detections"].append({
                    "label": det["label"], "confidence": det["confidence"],
                    "uncertainty": det["uncertainty"], "world_xyz": list(world_xyz),
                    "size_m": size_m, "defect_id": defect_id, "is_new": is_new, "growth": growth,
                })

            belief.record_visit(vp)
            steps.append(step_record)
            current_id = vp.id

        mean_entropy = float(np.mean([belief.coverage_entropy(w, c)
                                       for w in wall_names for c in range(N_CELLS)]))
    house.close()

    return {
        "planner": planner_name, "scenario": scenario.name, "mission_index": mission_index,
        "steps": steps, "total_dist": total_dist, "n_viewpoints": budget,
        "wall_detections": wall_detections, "ground_truth": gt,
        "final_mean_entropy": mean_entropy,
    }
