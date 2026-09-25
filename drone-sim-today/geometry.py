"""Shared camera/plane math, used by both dataset labeling (datagen/) and
runtime 3D defect localization (experiments/, demo_uwtig_flight.py).

Reproduces the exact camera convention gym-pybullet-drones' BaseAviary
_getDroneImages() uses (see gpd_src/gym_pybullet_drones/envs/BaseAviary.py):
eye = drone_pos + [0, 0, L], looking along the body's local +x axis, world
+z up, vertical FOV 60 deg, aspect FIXED at 1.0 (not IMG_RES's actual
aspect ratio -- the drone image is rendered slightly stretched, and every
projection here must match that exactly or 3D localization will be biased).
"""
import math

import numpy as np
import pybullet as p

FOV_DEG = 60.0
ASPECT = 1.0  # matches BaseAviary._getDroneImages, not IMG_RES's real aspect
NEAR = 0.05
FAR = 1000.0


def drone_camera_matrices(pos, quat, cam_offset_z=0.0, near=NEAR, far=FAR):
    """view, proj matrices for a camera rigidly mounted on a drone at `pos`
    (world xyz) / `quat` (world orientation, xyzw), matching BaseAviary's
    onboard camera exactly (cam_offset_z is BaseAviary's `self.L`)."""
    rot_mat = np.array(p.getMatrixFromQuaternion(quat)).reshape(3, 3)
    eye = np.array(pos) + np.array([0.0, 0.0, cam_offset_z])
    target = rot_mat @ np.array([1000.0, 0.0, 0.0]) + np.array(pos)
    view = p.computeViewMatrix(cameraEyePosition=eye, cameraTargetPosition=target,
                                cameraUpVector=[0, 0, 1])
    proj = p.computeProjectionMatrixFOV(fov=FOV_DEG, aspect=ASPECT, nearVal=near, farVal=far)
    return np.array(view).reshape(4, 4, order="F"), np.array(proj).reshape(4, 4, order="F")


def pixel_ray(u, v, view, proj, img_w, img_h):
    """Given a pixel (u, v) in image space (0..img_w, 0..img_h, y-down as
    OpenCV/PyBullet return frames), returns (origin, direction) of the
    world-space ray through that pixel, direction normalized."""
    ndc_x = (2.0 * u / img_w) - 1.0
    ndc_y = 1.0 - (2.0 * v / img_h)  # flip: image y-down -> NDC y-up

    inv_vp = np.linalg.inv(proj @ view)

    near_clip = np.array([ndc_x, ndc_y, -1.0, 1.0])
    far_clip = np.array([ndc_x, ndc_y, 1.0, 1.0])
    near_world = inv_vp @ near_clip
    far_world = inv_vp @ far_clip
    near_world /= near_world[3]
    far_world /= far_world[3]

    origin = near_world[:3]
    direction = far_world[:3] - near_world[:3]
    direction = direction / np.linalg.norm(direction)
    return origin, direction


def wall_plane(wall):
    """(point_on_plane, normal, u_axis, v_axis) for a WALL_SEGMENTS-style
    dict {x, y, yaw, width} (see sim_house.WALL_SEGMENTS), matching
    scene/wall_quad.obj's local-XZ-plane-facing-(-y) convention exactly:
    world = (x,y,Z_CENTER) + lx*(width/2)*u_axis + lz*(WALL_HEIGHT/2)*v_axis,
    normal = (sin(yaw), -cos(yaw), 0)."""
    yaw_rad = math.radians(wall["yaw"])
    normal = np.array([math.sin(yaw_rad), -math.cos(yaw_rad), 0.0])
    u_axis = np.array([math.cos(yaw_rad), math.sin(yaw_rad), 0.0])  # local +x -> world
    v_axis = np.array([0.0, 0.0, 1.0])  # local +z -> world, always vertical
    z_center = wall.get("z_center", 1.2)
    point = np.array([wall["x"], wall["y"], z_center])
    return point, normal, u_axis, v_axis


def ray_plane_intersect(origin, direction, plane_point, plane_normal):
    """Returns world xyz of intersection, or None if ray is parallel/behind."""
    denom = np.dot(direction, plane_normal)
    if abs(denom) < 1e-8:
        return None
    t = np.dot(plane_point - origin, plane_normal) / denom
    if t < 0:
        return None
    return origin + t * direction


def localize_on_wall(pixel_xy, drone_pos, drone_quat, wall, img_w, img_h, cam_offset_z=0.0):
    """Full pipeline: pixel -> ray -> intersection with the given wall's
    plane -> world xyz. Returns None if the ray misses the wall plane."""
    view, proj = drone_camera_matrices(drone_pos, drone_quat, cam_offset_z=cam_offset_z)
    origin, direction = pixel_ray(pixel_xy[0], pixel_xy[1], view, proj, img_w, img_h)
    point, normal, _, _ = wall_plane(wall)
    return ray_plane_intersect(origin, direction, point, normal)


def texture_uv_to_world(wall, px, py, tex_size=512, wall_height=2.4):
    """Analytic inverse of scene/wall_quad.obj's UV mapping: given a pixel
    (px, py) in a `tex_size`x`tex_size` wall texture (image convention,
    y-down), returns the world xyz of that point once the texture is bound
    to `wall`. Empirically validated (<2cm residual) against the
    ray-plane-intersection path in localize_on_wall for a known marker.
    Used as ground truth for localization-error scoring in experiments/,
    where scenarios place a defect at a known, controlled texture center
    instead of rendering a per-frame label pass (too slow for the batch
    kinematic comparison)."""
    u = px / tex_size
    v = 1.0 - py / tex_size
    point, _, u_axis, v_axis = wall_plane(wall)
    half_width = wall["width"] / 2
    return point + (2 * u - 1) * half_width * u_axis + (2 * v - 1) * (wall_height / 2) * v_axis


def wall_local_extent(world_points, wall):
    """Projects a list of world xyz points onto a wall's (u_axis, v_axis)
    basis, returning (span_u_m, span_v_m) -- used to turn a detection's
    world-projected bounding corners into a physical size in meters for
    growth tracking, without needing texture-UV math."""
    _, _, u_axis, v_axis = wall_plane(wall)
    us = [np.dot(pt, u_axis) for pt in world_points]
    vs = [np.dot(pt, v_axis) for pt in world_points]
    return max(us) - min(us), max(vs) - min(vs)
