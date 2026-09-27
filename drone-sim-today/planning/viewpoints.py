"""Candidate viewpoint graph over the sim_house.WALL_SEGMENTS layout: for
each wall, a small set of (standoff distance x lateral offset) stations,
each with a known 3D pose and the span of the wall's surface it can see.
Used by all three planners and by experiments/kinematic_capture.py.
"""
import math
from dataclasses import dataclass, field

import numpy as np

import geometry as geo

STANDOFFS = [0.8, 1.3]
LATERAL_FRACS = [-0.55, 0.0, 0.55]  # fraction of half-width, keeps FOV within the wall
FLIGHT_Z = 1.2

# Surface-coverage discretization: a FIXED PHYSICAL cell size, not a fixed
# cell count per wall -- matching Isler et al. (2016)'s original volumetric
# formulation, where voxel SIZE is fixed and a bigger volume simply has more
# voxels. A fixed cell COUNT was tried first and is wrong: it makes a narrow
# wall's single viewpoint "see" its whole (tiny) surface at once, giving it
# a disproportionately high per-viewpoint information gain relative to a
# wide wall (where the same viewpoint only ever sees a fraction of it) --
# the planner then greedily exhausts every viewpoint on the narrow walls
# and never gets pulled toward the wide, still-uncovered ones. Confirmed
# via a quick sweep: fixed-count-4 made UW-TIG freeze on the 1.2m inspection
# panels for an entire mission (flight_dist == 0.0) once real walls ranged
# from 1.2m to 4.0m wide (the old layout's 1.5-4.0m range hid this).
CELL_WIDTH_M = 1.0


def n_cells_for_wall(wall):
    return max(1, round(wall["width"] / CELL_WIDTH_M))

# Approx horizontal half-FOV in world units at a given standoff, matching the
# 60deg vertical FOV / aspect=1.0 camera in geometry.py closely enough for
# visibility-span bookkeeping (not used for anything pixel-exact).
HALF_FOV_RAD = math.radians(30)


@dataclass
class Viewpoint:
    id: str
    wall: str
    pos: np.ndarray
    yaw_deg: float
    standoff: float
    lateral: float
    visible_cells: list = field(default_factory=list)  # cell indices on `wall` this can see


def _wall_lookup(wall_segments):
    return {w["name"]: w for w in wall_segments}


def build_viewpoints(wall_segments):
    """Returns (viewpoints: list[Viewpoint], dist: dict[(id,id)] -> meters)."""
    viewpoints = []
    for wall in wall_segments:
        point, normal, u_axis, v_axis = geo.wall_plane(wall)
        half_width = wall["width"] / 2
        for standoff in STANDOFFS:
            for frac in LATERAL_FRACS:
                lateral = frac * half_width
                pos = point + standoff * normal + lateral * u_axis
                pos[2] = FLIGHT_Z
                approach_yaw = wall["yaw"] + 90
                vid = f"{wall['name']}|s{standoff:.1f}|l{frac:+.2f}"

                visible_half_span = standoff * math.tan(HALF_FOV_RAD)
                lo_u, hi_u = lateral - visible_half_span, lateral + visible_half_span
                n_cells = n_cells_for_wall(wall)
                cell_w = wall["width"] / n_cells
                visible_cells = []
                for c in range(n_cells):
                    cell_lo = -half_width + c * cell_w
                    cell_hi = cell_lo + cell_w
                    if cell_hi > lo_u and cell_lo < hi_u:
                        visible_cells.append(c)

                viewpoints.append(Viewpoint(
                    id=vid, wall=wall["name"], pos=pos, yaw_deg=approach_yaw,
                    standoff=standoff, lateral=lateral, visible_cells=visible_cells,
                ))

    dist = {}
    for a in viewpoints:
        for b in viewpoints:
            dist[(a.id, b.id)] = float(np.linalg.norm(a.pos - b.pos))
    return viewpoints, dist


def cell_index_for_world_point(wall, world_point):
    """Maps a world xyz (assumed already on/near `wall`'s plane, e.g. from
    geometry.localize_on_wall) to its coverage-grid cell index."""
    _, _, u_axis, _ = geo.wall_plane(wall)
    point, _, _, _ = geo.wall_plane(wall)
    u = np.dot(np.array(world_point) - point, u_axis)
    half_width = wall["width"] / 2
    n_cells = n_cells_for_wall(wall)
    cell_w = wall["width"] / n_cells
    idx = int((u + half_width) // cell_w)
    return int(np.clip(idx, 0, n_cells - 1))
