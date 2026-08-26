"""Autonomous drone flight simulation with an onboard camera sensor.

Kinematic autopilot (not full flight dynamics): the drone body is moved
along a scripted waypoint path with no manual input, which is enough to
demonstrate "autonomous flight + onboard sensing" for today's prototype.
Full PX4-style flight control is out of scope for this stand-in.
"""
import math
import os
import time

import numpy as np
import pybullet as p
import pybullet_data

SCENE_DIR = os.path.join(os.path.dirname(__file__), "scene")
CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(CAPTURE_DIR, exist_ok=True)

IMG_W, IMG_H = 480, 360

# Each wall: x position along the flight corridor, texture file, ground-truth label
WALLS = [
    (-9, "clean_wall_1.png", "clean"),
    (-6, "crack_wall_1.png", "crack"),
    (-3, "clean_wall_2.png", "clean"),
    (0, "rust_wall_1.png", "rust"),
    (3, "crack_wall_2.png", "crack"),
    (6, "leak_wall_1.png", "leak"),
    (9, "clean_wall_3.png", "clean"),
]
WALL_Y = 3.0
WALL_Z = 1.5
DRONE_Y = 0.0
DRONE_Z = 1.5


def connect(gui=True):
    client = p.connect(p.GUI if gui else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -9.8, physicsClientId=client)
    return client


WALL_QUAD_OBJ = os.path.join(SCENE_DIR, "wall_quad.obj")


def build_scene(client):
    p.loadURDF("plane.urdf", physicsClientId=client)
    wall_infos = []
    for x, texture_file, label in WALLS:
        # GEOM_BOX primitives carry no UVs, so textures silently no-op on them;
        # use a textured quad mesh instead.
        vis = p.createVisualShape(
            p.GEOM_MESH, fileName=WALL_QUAD_OBJ, meshScale=[1.2, 1, 1.4],
            rgbaColor=[1, 1, 1, 1], physicsClientId=client,
        )
        body = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=vis,
            basePosition=[x, WALL_Y, WALL_Z],
            physicsClientId=client,
        )
        tex_path = os.path.join(SCENE_DIR, texture_file)
        tex_id = p.loadTexture(tex_path, physicsClientId=client)
        p.changeVisualShape(body, -1, textureUniqueId=tex_id, physicsClientId=client)
        wall_infos.append({"body": body, "pos": (x, WALL_Y, WALL_Z), "label": label, "texture": texture_file})
    return wall_infos


def create_drone(client, start_pos=(-11, DRONE_Y, DRONE_Z)):
    body_r, arm_len = 0.12, 0.28
    body_col = p.createCollisionShape(p.GEOM_SPHERE, radius=body_r, physicsClientId=client)
    body_vis = p.createVisualShape(p.GEOM_SPHERE, radius=body_r, rgbaColor=[0.1, 0.1, 0.1, 1], physicsClientId=client)
    drone = p.createMultiBody(
        baseMass=0,
        baseCollisionShapeIndex=body_col,
        baseVisualShapeIndex=body_vis,
        basePosition=list(start_pos),
        physicsClientId=client,
    )
    rotor_ids = []
    for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        rvis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.08, length=0.02,
                                    rgbaColor=[0.8, 0.2, 0.2, 1], physicsClientId=client)
        rotor = p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=rvis,
            basePosition=[start_pos[0] + dx * arm_len, start_pos[1] + dy * arm_len, start_pos[2]],
            physicsClientId=client,
        )
        rotor_ids.append((rotor, dx, dy))
    return drone, rotor_ids, arm_len


def set_drone_pose(client, drone, rotor_ids, arm_len, pos, spin_phase=0.0):
    p.resetBasePositionAndOrientation(drone, pos, [0, 0, 0, 1], physicsClientId=client)
    for rotor, dx, dy in rotor_ids:
        wobble = 0.01 * math.sin(spin_phase * 6 + dx + dy)
        rpos = [pos[0] + dx * arm_len, pos[1] + dy * arm_len, pos[2] + wobble]
        p.resetBasePositionAndOrientation(rotor, rpos, [0, 0, 0, 1], physicsClientId=client)


def capture_from_drone(client, drone_pos, target_pos):
    view = p.computeViewMatrix(cameraEyePosition=drone_pos, cameraTargetPosition=target_pos,
                                cameraUpVector=[0, 0, 1])
    proj = p.computeProjectionMatrixFOV(fov=60, aspect=IMG_W / IMG_H, nearVal=0.05, farVal=20)
    _, _, rgba, _, _ = p.getCameraImage(IMG_W, IMG_H, view, proj,
                                         renderer=p.ER_BULLET_HARDWARE_OPENGL,
                                         physicsClientId=client)
    rgb = np.reshape(rgba, (IMG_H, IMG_W, 4))[:, :, :3].astype(np.uint8)
    return rgb


def lerp(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(3)]


def fly_mission(gui=True, steps_between=40, hover_steps=25, sleep_dt=1.0 / 240.0):
    """Runs the full autonomous waypoint mission. Yields (frame_idx, rgb, wall_info_or_None)."""
    client = connect(gui=gui)
    walls = build_scene(client)
    drone, rotors, arm_len = create_drone(client)

    waypoints = [(x, DRONE_Y, DRONE_Z) for x, _, _ in WALLS]
    current = (-11, DRONE_Y, DRONE_Z)
    frame_idx = 0
    phase = 0.0

    for wi, target_xyz in enumerate(waypoints):
        for s in range(steps_between):
            t = (s + 1) / steps_between
            pos = lerp(current, target_xyz, t)
            phase += 0.05
            set_drone_pose(client, drone, rotors, arm_len, pos, phase)
            p.stepSimulation(physicsClientId=client)
            if gui:
                time.sleep(sleep_dt)
        current = target_xyz

        wall = walls[wi]
        for h in range(hover_steps):
            phase += 0.05
            set_drone_pose(client, drone, rotors, arm_len, current, phase)
            p.stepSimulation(physicsClientId=client)
            if gui:
                time.sleep(sleep_dt)

        rgb = capture_from_drone(client, list(current), list(wall["pos"]))
        frame_idx += 1
        yield frame_idx, rgb, wall

    p.disconnect(physicsClientId=client)


if __name__ == "__main__":
    import cv2
    for idx, rgb, wall in fly_mission(gui=False):
        out_path = os.path.join(CAPTURE_DIR, f"frame_{idx:02d}_{wall['label']}.png")
        cv2.imwrite(out_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        print(f"[{idx}] captured at wall x={wall['pos'][0]} label={wall['label']} -> {out_path}")
    print("Mission complete.")
