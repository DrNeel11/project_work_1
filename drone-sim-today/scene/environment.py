"""Open-air utility yard dressing: sky backdrop, ground texture, and
decorative pipe-rack/lattice-tower structures (each now carrying one real,
inspectable panel -- see sim_house.WALL_SEGMENTS' "PipeRack-Panel" and
"Tower-Panel" entries, positioned to match PIPE_RACK_POS/TOWER_POS below).
Everything in this module except the two panel *mounting positions* is
purely visual: static (mass=0) bodies with no bearing on wall geometry,
planning, or detection.

Unlike the old enclosed-house dressing, the sky backdrop and yard are
visible for the entire flight (freestanding structures, real open sky
between them), not just a one-off establishing shot.
"""
import math
import os

import numpy as np
import pybullet as p
from PIL import Image, ImageDraw

SCENE_DIR = os.path.dirname(os.path.abspath(__file__))
GROUND_TEXTURE_PATH = os.path.join(SCENE_DIR, "ground_concrete.png")
SKY_TEXTURE_PATH = os.path.join(SCENE_DIR, "sky_backdrop.png")

PIPE_COLOR = (0.55, 0.58, 0.6, 1.0)
RUST_ACCENT = (0.45, 0.3, 0.22, 1.0)
PYLON_COLOR = (0.35, 0.37, 0.4, 1.0)
CRATE_COLOR = (0.5, 0.38, 0.22, 1.0)
BARREL_COLOR = (0.15, 0.35, 0.2, 1.0)

# Kept in sync with sim_house.WALL_SEGMENTS' "PipeRack-Panel"/"Tower-Panel"
# (x, y) so the real inspection panel appears mounted on the decorative
# structure rather than floating unrelated to it.
PIPE_RACK_POS = (7.0, 4.0)
TOWER_POS = (-5.0, 3.0)

YARD_CENTER = (5.0, 1.5)  # roughly the centroid of the whole layout


def ensure_ground_texture(size=1024):
    """Procedurally generates a mottled concrete/gravel-yard texture once,
    caching it to disk (same generate-once-reuse pattern as scene/make_textures.py).
    Higher resolution than the original pass plus oil stains, tire marks, and
    an expansion-joint grid (real poured-concrete yards are scored into
    rectangular slabs, not a featureless blob) -- a pure presentation/context
    improvement: this texture is never in the onboard detection camera's
    tightly-framed, wall-facing field of view (see module docstring), so it
    has no effect on any detection metric."""
    if os.path.exists(GROUND_TEXTURE_PATH):
        return GROUND_TEXTURE_PATH

    rng = np.random.RandomState(11)
    base = np.full((size, size, 3), (150, 148, 142), dtype=np.int16)
    base += rng.randint(-14, 15, size=(size, size, 3))
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

    draw = ImageDraw.Draw(img, "RGBA")
    # Expansion-joint grid: real poured slabs are scored into rectangles
    slab = size // 6
    for i in range(1, 6):
        draw.line([(i * slab, 0), (i * slab, size)], fill=(100, 98, 94, 160), width=3)
        draw.line([(0, i * slab), (size, i * slab)], fill=(100, 98, 94, 160), width=3)
    for _ in range(70):  # mottled weathering stains/patches
        cx, cy = rng.randint(0, size), rng.randint(0, size)
        r = rng.randint(20, 90)
        shade = rng.randint(-25, 10)
        col = (150 + shade, 148 + shade, 142 + shade, 55)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    for _ in range(45):  # fine surface cracks within slabs
        x0, y0 = rng.randint(0, size), rng.randint(0, size)
        length = rng.randint(50, 220)
        angle = rng.uniform(0, 2 * math.pi)
        x1 = int(np.clip(x0 + length * math.cos(angle), 0, size))
        y1 = int(np.clip(y0 + length * math.sin(angle), 0, size))
        draw.line([(x0, y0), (x1, y1)], fill=(90, 88, 84, 130), width=2)
    for _ in range(10):  # dark oil/fluid stains near equipment
        cx, cy = rng.randint(0, size), rng.randint(0, size)
        rx, ry = rng.randint(25, 70), rng.randint(18, 45)
        shade = rng.randint(35, 55)
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(shade, shade, shade, 90))
    for _ in range(4):  # paired tire-mark streaks
        x0 = rng.randint(0, size)
        y0 = rng.randint(0, size)
        angle = rng.uniform(0, 2 * math.pi)
        length = rng.randint(200, 420)
        dx, dy = math.cos(angle), math.sin(angle)
        perp = (-dy, dx)
        for off in (-14, 14):
            sx, sy = x0 + perp[0] * off, y0 + perp[1] * off
            ex, ey = sx + dx * length, sy + dy * length
            draw.line([(sx, sy), (ex, ey)], fill=(70, 68, 65, 70), width=9)

    img.save(GROUND_TEXTURE_PATH)
    return GROUND_TEXTURE_PATH


def retexture_ground(client, plane_id):
    """Applies the concrete yard texture to an already-loaded plane.urdf
    body (BaseAviary loads one on every reset() as self.PLANE_ID). The
    plane itself is effectively infinite, so this covers the larger
    open-yard layout with no other change needed."""
    tex_path = ensure_ground_texture()
    tex_id = p.loadTexture(tex_path, physicsClientId=client)
    p.changeVisualShape(plane_id, -1, textureUniqueId=tex_id, physicsClientId=client)


def ensure_sky_texture(size=1024):
    """A vertical sky gradient (blue overhead fading to a pale horizon), a
    soft sun glow, a few low clouds, and a distant-skyline silhouette with
    lit windows baked into the bottom band -- applied to 4 big cyclorama
    walls (add_sky_backdrop) so the horizon reads as sky everywhere, not a
    flat white void, for the whole flight. Higher resolution and more detail
    than the original pass; still a flat painted backdrop, not real sky
    geometry or a dynamic light source -- this is a presentation/context
    improvement only (the onboard detection camera stays tightly framed on
    the wall it's inspecting, see module docstring), so it has no effect on
    any detection metric."""
    if os.path.exists(SKY_TEXTURE_PATH):
        return SKY_TEXTURE_PATH

    top_color = np.array([98, 152, 214])
    horizon_color = np.array([221, 229, 232])
    grad = np.zeros((size, size, 3), dtype=np.uint8)
    for y in range(size):
        t = min(1.0, (y / size) / 0.78)
        grad[y, :, :] = (top_color * (1 - t) + horizon_color * t).astype(np.uint8)
    img = Image.fromarray(grad)
    draw = ImageDraw.Draw(img, "RGBA")

    # Soft sun glow -- a radial falloff blended additively onto one corner
    sun_x, sun_y = int(size * 0.78), int(size * 0.22)
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for r, a in [(220, 10), (160, 16), (110, 22), (65, 30), (30, 40)]:
        glow_draw.ellipse([sun_x - r, sun_y - r, sun_x + r, sun_y + r], fill=(255, 250, 230, a))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    draw = ImageDraw.Draw(img, "RGBA")

    rng = np.random.RandomState(7)
    # A few soft, low clouds well above the skyline
    for _ in range(6):
        cx = rng.randint(0, size)
        cy = rng.randint(int(size * 0.25), int(size * 0.55))
        for _ in range(5):
            ox, oy = rng.randint(-60, 60), rng.randint(-15, 15)
            r = rng.randint(30, 70)
            draw.ellipse([cx + ox - r, cy + oy - r // 2, cx + ox + r, cy + oy + r // 2],
                         fill=(255, 255, 255, 35))

    rng = np.random.RandomState(42)
    base_y = int(size * 0.80)
    x = 0
    while x < size:
        w = rng.randint(28, 95)
        h = rng.randint(25, 170)
        shade = rng.randint(85, 140)
        draw.rectangle([x, base_y - h, x + w, size], fill=(shade, shade, shade + 6, 255))
        # Lit windows: a sparse grid of small warm-colored squares
        if h > 50:
            win_rng = np.random.RandomState(x)
            for wy in range(base_y - h + 8, size - 8, 14):
                for wx in range(x + 4, x + w - 4, 10):
                    if win_rng.random() < 0.35:
                        draw.rectangle([wx, wy, wx + 4, wy + 7], fill=(255, 221, 150, 200))
        x += w + rng.randint(2, 14)

    img.convert("RGB").save(SKY_TEXTURE_PATH)
    return SKY_TEXTURE_PATH


WALL_QUAD_OBJ = os.path.join(SCENE_DIR, "wall_quad.obj")


def add_sky_backdrop(client, center=YARD_CENTER, half_extent=45.0, wall_height=40.0):
    """4 large textured cyclorama walls surrounding the whole yard, tall
    enough to fill the background at every camera angle actually used
    (station captures, transit, the orbiting establishing shot). Built from
    the same flat-quad mesh (wall_quad.obj) and yaw-to-normal convention as
    the real inspection walls in sim_house.WALL_SEGMENTS, each face rotated
    to point inward toward the yard -- GEOM_BOX primitives were tried first
    but PyBullet tiles/repeats a box's texture across its extents rather
    than stretching one copy per face (confirmed by direct render-and-look
    testing, not assumed), which fractured the skyline into several
    tiny repeats; the mesh quad is the same approach already proven correct
    for every real defect texture in this project, so it was reused here
    too rather than fighting the primitive's UV behavior."""
    tex_id = p.loadTexture(ensure_sky_texture(), physicsClientId=client)
    cx, cy = center
    z = wall_height / 2
    # (x, y, yaw): yaw follows sim_house's normal = (sin(yaw), -cos(yaw), 0)
    # convention, chosen so each wall's visible face points toward the yard.
    specs = [
        (cx, cy + half_extent, 0),
        (cx, cy - half_extent, 180),
        (cx + half_extent, cy, -90),
        (cx - half_extent, cy, 90),
    ]
    bodies = []
    for x, y, yaw in specs:
        vis = p.createVisualShape(p.GEOM_MESH, fileName=WALL_QUAD_OBJ,
                                   meshScale=[half_extent, 1, wall_height / 2],
                                   rgbaColor=[1, 1, 1, 1], physicsClientId=client)
        orn = p.getQuaternionFromEuler([0, 0, math.radians(yaw)])
        body = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis,
                                  basePosition=[x, y, z], baseOrientation=orn,
                                  physicsClientId=client)
        p.changeVisualShape(body, -1, textureUniqueId=tex_id, physicsClientId=client)
        bodies.append(body)
    return bodies


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


def _pipe_rack(client):
    """Elevated pipe rack along y at PIPE_RACK_POS's x, centered on
    PIPE_RACK_POS's y -- the middle pylon sits exactly where
    sim_house.WALL_SEGMENTS' "PipeRack-Panel" is mounted."""
    x, y_mid = PIPE_RACK_POS
    pylon_ys = [y_mid - 2.0, y_mid, y_mid + 2.0]
    rack_h = 2.0
    bodies = [_pylon(client, x, y, height=rack_h) for y in pylon_ys]
    for y0, y1 in zip(pylon_ys[:-1], pylon_ys[1:]):
        bodies.append(_horizontal_pipe(client, (x, y0, rack_h), (x, y1, rack_h)))
        bodies.append(_horizontal_pipe(client, (x, y0, rack_h - 0.4), (x, y1, rack_h - 0.4),
                                        radius=0.10, rgba=RUST_ACCENT))
    return bodies


def _lattice_tower(client):
    """Two-pylon lattice tower accent at TOWER_POS -- the near pylon sits
    exactly where sim_house.WALL_SEGMENTS' "Tower-Panel" is mounted."""
    x, y = TOWER_POS
    tower_h = 3.2
    bodies = [_pylon(client, x, y, height=tower_h, radius=0.10),
              _pylon(client, x - 1.2, y, height=tower_h, radius=0.10)]
    for h in (0.8, 1.8, 2.8):
        bodies.append(_horizontal_pipe(client, (x, y, h), (x - 1.2, y, h), radius=0.06))
        if h < 2.8:
            bodies.append(_horizontal_pipe(client, (x, y, h), (x - 1.2, y, h + 1.0), radius=0.045))
    return bodies


def _ground_clutter(client, rng_seed=7):
    """A handful of crates/barrels scattered near the structures for
    lived-in realism -- purely decorative, well clear of every flight
    viewpoint (planning/viewpoints.py stays within ~3m of each wall)."""
    rng = np.random.RandomState(rng_seed)
    bodies = []
    spots = [(-3.2, -3.5), (3.5, -3.3), (9.5, -2.5), (17.5, 2.0), (2.5, 5.5), (-6.5, -1.0)]
    for x, y in spots:
        if rng.random() < 0.5:
            s = rng.uniform(0.22, 0.34)
            bodies.append(_box(client, [s, s, s], [x, y, s], CRATE_COLOR,
                                orn=p.getQuaternionFromEuler([0, 0, rng.uniform(0, math.pi)])))
        else:
            r = rng.uniform(0.18, 0.24)
            h = rng.uniform(0.5, 0.7)
            bodies.append(_cylinder(client, r, h, [x, y, h / 2], BARREL_COLOR))
    return bodies


def add_decorative_props(client):
    """Adds the sky backdrop, pipe rack, lattice tower, and ground clutter.
    Called once per fresh scene by sim_house.build_house(), shared by both
    the kinematic sim and the real-physics flagship demo."""
    bodies = []
    bodies += add_sky_backdrop(client)
    bodies += _pipe_rack(client)
    bodies += _lattice_tower(client)
    bodies += _ground_clutter(client)
    return bodies
