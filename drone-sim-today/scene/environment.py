"""Non-inspectable environment dressing: a concrete ground texture and
decorative pipe-rack/support-pylon geometry scattered outside the house
footprint, so the scene reads as a utility inspection yard rather than a
house tour. Purely visual -- static (mass=0) bodies with no bearing on
wall geometry, planning, or detection, so this can't affect any of the
localization/planning math the rest of the system depends on.

Placed well outside the flight envelope (all viewpoints stay within roughly
x in [-3, 3], y in [-1, 6.5] -- see planning/viewpoints.py), so the props are
visible in the wide third-person flythrough without ever entering an
inspection camera's frame.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw

import pybullet as p

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
GROUND_TEXTURE_PATH = os.path.join(SCENE_DIR, "ground_concrete.png")

PIPE_COLOR = (0.55, 0.58, 0.6, 1.0)
RUST_ACCENT = (0.45, 0.3, 0.22, 1.0)
PYLON_COLOR = (0.35, 0.37, 0.4, 1.0)


def ensure_ground_texture(size=512):
    """Procedurally generates a mottled concrete/gravel-yard texture once,
    caching it to disk (same generate-once-reuse pattern as scene/make_textures.py)."""
    if os.path.exists(GROUND_TEXTURE_PATH):
        return GROUND_TEXTURE_PATH

    rng = np.random.RandomState(11)
    base = np.full((size, size, 3), (150, 148, 142), dtype=np.int16)
    base += rng.randint(-14, 15, size=(size, size, 3))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

    draw = ImageDraw.Draw(img, "RGBA")
    for _ in range(40):  # mottled stains/patches
        cx, cy = rng.randint(0, size), rng.randint(0, size)
        r = rng.randint(15, 45)
        shade = rng.randint(-25, 10)
        col = (150 + shade, 148 + shade, 142 + shade, 60)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    for _ in range(25):  # expansion-joint-style cracks/lines
        x0, y0 = rng.randint(0, size), rng.randint(0, size)
        length = rng.randint(40, 160)
        angle = rng.uniform(0, 2 * math.pi)
        x1 = int(np.clip(x0 + length * math.cos(angle), 0, size))
        y1 = int(np.clip(y0 + length * math.sin(angle), 0, size))
        draw.line([(x0, y0), (x1, y1)], fill=(90, 88, 84, 140), width=2)

    img.save(GROUND_TEXTURE_PATH)
    return GROUND_TEXTURE_PATH


def retexture_ground(client, plane_id):
    """Applies the concrete yard texture to an already-loaded plane.urdf
    body (BaseAviary loads one on every reset() as self.PLANE_ID)."""
    tex_path = ensure_ground_texture()
    tex_id = p.loadTexture(tex_path, physicsClientId=client)
    p.changeVisualShape(plane_id, -1, textureUniqueId=tex_id, physicsClientId=client)


def _box(client, half_extents, pos, rgba, orn=None):
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=half_extents, rgbaColor=rgba, physicsClientId=client)
    kwargs = dict(baseMass=0, baseVisualShapeIndex=vis, basePosition=pos, physicsClientId=client)
    if orn is not None:
        kwargs["baseOrientation"] = orn
    return p.createMultiBody(**kwargs)


def _cylinder(client, radius, length, pos, rgba, orn=None):
    vis = p.createVisualShape(p.GEOM_CYLINDER, radius=radius, length=length, rgbaColor=rgba,
                               physicsClientId=client)
    kwargs = dict(baseMass=0, baseVisualShapeIndex=vis, basePosition=pos, physicsClientId=client)
    if orn is not None:
        kwargs["baseOrientation"] = orn
    return p.createMultiBody(**kwargs)


def _pylon(client, x, y, height=3.0, radius=0.09):
    return _cylinder(client, radius, height, (x, y, height / 2), PYLON_COLOR)


def _horizontal_pipe(client, p0, p1, radius=0.14, rgba=PIPE_COLOR):
    p0, p1 = np.array(p0), np.array(p1)
    mid = (p0 + p1) / 2
    length = float(np.linalg.norm(p1 - p0))
    direction = (p1 - p0) / max(length, 1e-6)
    # cylinder's local axis is +z; rotate it to point along `direction`
    z_axis = np.array([0.0, 0.0, 1.0])
    axis = np.cross(z_axis, direction)
    angle = math.acos(float(np.clip(np.dot(z_axis, direction), -1.0, 1.0)))
    if np.linalg.norm(axis) < 1e-6:
        orn = [0, 0, 0, 1]
    else:
        axis = axis / np.linalg.norm(axis)
        orn = p.getQuaternionFromAxisAngle(axis.tolist(), angle)
    return _cylinder(client, radius, length, mid.tolist(), rgba, orn=orn)


def add_decorative_props(client):
    """Adds a small pipe-rack + support-pylon cluster on each side of the
    house, outside the flight envelope. Called once per fresh scene by
    sim_house.build_house(), shared by both the kinematic sim and the
    real-physics flagship demo."""
    bodies = []

    # East yard: elevated pipe rack on 4 pylons, mimicking a utility corridor.
    east_x = 6.5
    pylon_ys = [-1.5, 1.5, 4.0]
    rack_h = 2.0
    for y in pylon_ys:
        bodies.append(_pylon(client, east_x, y, height=rack_h))
    for y0, y1 in zip(pylon_ys[:-1], pylon_ys[1:]):
        bodies.append(_horizontal_pipe(client, (east_x, y0, rack_h), (east_x, y1, rack_h)))
        bodies.append(_horizontal_pipe(client, (east_x, y0, rack_h - 0.4), (east_x, y1, rack_h - 0.4),
                                        radius=0.10, rgba=RUST_ACCENT))

    # West yard: a small lattice/truss tower accent (two pylons + cross-braces).
    west_x = -6.5
    tower_h = 3.2
    bodies.append(_pylon(client, west_x, 0.0, height=tower_h, radius=0.10))
    bodies.append(_pylon(client, west_x - 1.2, 0.0, height=tower_h, radius=0.10))
    for h in (0.8, 1.8, 2.8):
        bodies.append(_horizontal_pipe(client, (west_x, 0.0, h), (west_x - 1.2, 0.0, h), radius=0.06))
        # diagonal cross-brace between consecutive rungs
        if h < 2.8:
            bodies.append(_horizontal_pipe(client, (west_x, 0.0, h), (west_x - 1.2, 0.0, h + 1.0), radius=0.045))

    return bodies
