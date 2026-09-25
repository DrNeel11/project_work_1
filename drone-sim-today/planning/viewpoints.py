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
N_CELLS = 4  # surface-coverage discretization per wall, along its width

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
                cell_w = wall["width"] / N_CELLS
                visible_cells = []
                for c in range(N_CELLS):
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
    geometry.localize_on_wall) to its coverage-grid cell index [0, N_CELLS)."""
    _, _, u_axis, _ = geo.wall_plane(wall)
    point, _, _, _ = geo.wall_plane(wall)
    u = np.dot(np.array(world_point) - point, u_axis)
    half_width = wall["width"] / 2
    cell_w = wall["width"] / N_CELLS
    idx = int((u + half_width) // cell_w)
    return int(np.clip(idx, 0, N_CELLS - 1))
