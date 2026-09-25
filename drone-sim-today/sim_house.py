"""A small two-room house environment for the autonomous inspection drone,
built on the same gym-pybullet-drones physics/PID flight stack as
sim_gpd.py. Room A (4x4m) connects to the smaller Room B (2.6x2.6m)
through a 1m doorway gap in the shared wall. The drone autonomously
patrols both rooms, station-keeping and yawing to face each wall panel
in turn for its onboard camera to inspect.
"""
import math
import os

import cv2
import numpy as np
import pybullet as p

from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl
from gym_pybullet_drones.utils.enums import DroneModel, Physics

from scene.environment import add_decorative_props
from sim_gpd import VisionCtrlAviary

SCENE_DIR = os.path.join(os.path.dirname(__file__), "scene")
CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(CAPTURE_DIR, exist_ok=True)
WALL_QUAD_OBJ = os.path.join(SCENE_DIR, "wall_quad.obj")

WALL_HEIGHT = 2.4
Z_CENTER = WALL_HEIGHT / 2
FLIGHT_Z = 1.2
IMG_RES = np.array([320, 240])

# Each wall segment: (center_x, center_y, yaw_deg, width, texture, label)
# yaw_deg is the mesh's own facing direction (its face normal points into
# whichever room it borders); see the yaw-to-normal derivation this was
# built from: normal = (sin(yaw), -cos(yaw), 0).
WALL_SEGMENTS = [
    # --- Room A (4m x 4m), centered at origin ---
    dict(name="A-west", x=-2.0, y=0.0, yaw=90, width=4.0, texture="crack_wall_1.png", label="crack"),
    dict(name="A-east", x=2.0, y=0.0, yaw=-90, width=4.0, texture="rust_wall_1.png", label="rust"),
    dict(name="A-south", x=0.0, y=-2.0, yaw=180, width=4.0, texture="clean_wall_1.png", label="clean"),
    # North wall of room A has a 1m doorway gap into room B, so it's built
    # from two 1.5m segments flanking the gap instead of one 4m panel.
    dict(name="A-north-west", x=-1.25, y=2.0, yaw=0, width=1.5, texture="leak_wall_1.png", label="leak"),
    dict(name="A-north-east", x=1.25, y=2.0, yaw=0, width=1.5, texture="clean_wall_2.png", label="clean"),
    # --- Room B (2.6m x 2.6m), north of room A, sharing the doorway ---
    dict(name="B-west", x=-1.3, y=3.3, yaw=90, width=2.6, texture="clean_wall_3.png", label="clean"),
    dict(name="B-east", x=1.3, y=3.3, yaw=-90, width=2.6, texture="crack_wall_2.png", label="crack"),
    dict(name="B-north", x=0.0, y=4.6, yaw=180, width=2.6, texture="rust_wall_1.png", label="rust"),
]

# Patrol order: room A perimeter, transit through the doorway, room B
# perimeter. Transit waypoints (capture=False) keep the straight-line
# path between stations inside open floor space instead of clipping
# through walls (no collision is modeled — this is a kinematic-visual sim).
PATROL = [
    {"wall": "A-west", "capture": True},
    {"wall": "A-south", "capture": True},
    {"wall": "A-east", "capture": True},
    {"wall": "A-north-east", "capture": True},
    {"wall": "A-north-west", "capture": True},
    {"transit_pos": (0.0, 1.2, FLIGHT_Z), "transit_yaw": 90, "capture": False},
    {"wall": "B-west", "capture": True},
    {"wall": "B-east", "capture": True},
    {"wall": "B-north", "capture": True},
]

STANDOFF = {  # room A panels use a slightly bigger standoff than room B
    "A": 1.2,
    "B": 1.0,
}


def _wall_by_name(name):
    for w in WALL_SEGMENTS:
        if w["name"] == name:
            return w
    raise KeyError(name)


def _standoff_pose(wall):
    yaw_rad = math.radians(wall["yaw"])
    normal = np.array([math.sin(yaw_rad), -math.cos(yaw_rad), 0.0])
    standoff = STANDOFF[wall["name"][0]]
    pos = np.array([wall["x"], wall["y"], FLIGHT_Z]) + standoff * normal
    approach_yaw = wall["yaw"] + 90
    return pos, approach_yaw


# Third-person "chase cam" that follows behind and above the drone, so it
# stays clearly visible (a static wide shot makes the ~9cm airframe a
# barely-visible speck) while showing the walls/rooms scroll past as it
# flies — this is what actually reads as "watching the drone fly around".
OVERVIEW_RES = (480, 360)
CHASE_DIST = 0.8
CHASE_HEIGHT = 0.5
CHASE_LOOKAHEAD = 0.3


def _capture_overview(client, pos, quat):
    rot_mat = np.array(p.getMatrixFromQuaternion(quat)).reshape(3, 3)
    forward = rot_mat @ np.array([1.0, 0.0, 0.0])
    eye = pos - forward * CHASE_DIST + np.array([0, 0, CHASE_HEIGHT])
    target = pos + forward * CHASE_LOOKAHEAD
    view = p.computeViewMatrix(cameraEyePosition=eye, cameraTargetPosition=target,
                                cameraUpVector=[0, 0, 1])
    proj = p.computeProjectionMatrixFOV(fov=70, aspect=OVERVIEW_RES[0] / OVERVIEW_RES[1],
                                         nearVal=0.05, farVal=30)
    _, _, rgba, _, _ = p.getCameraImage(OVERVIEW_RES[0], OVERVIEW_RES[1], view, proj,
                                         physicsClientId=client)
    rgb = np.reshape(rgba, (OVERVIEW_RES[1], OVERVIEW_RES[0], 4))[:, :, :3].astype(np.uint8)
    return rgb


def build_house(client):
    infos = {}
    for wall in WALL_SEGMENTS:
        vis = p.createVisualShape(
            p.GEOM_MESH, fileName=WALL_QUAD_OBJ, meshScale=[wall["width"] / 2, 1, WALL_HEIGHT / 2],
            rgbaColor=[1, 1, 1, 1], physicsClientId=client,
        )
        orn = p.getQuaternionFromEuler([0, 0, math.radians(wall["yaw"])])
        body = p.createMultiBody(
            baseMass=0, baseVisualShapeIndex=vis,
            basePosition=[wall["x"], wall["y"], Z_CENTER], baseOrientation=orn,
            physicsClientId=client,
        )
        tex_id = p.loadTexture(os.path.join(SCENE_DIR, wall["texture"]), physicsClientId=client)
        p.changeVisualShape(body, -1, textureUniqueId=tex_id, physicsClientId=client)
        infos[wall["name"]] = body
    add_decorative_props(client)  # pipe rack / support pylons outside the flight envelope
    return infos


def fly_house_mission(gui=False, ctrl_freq=48, pyb_freq=240,
                       approach_steps=420, hover_steps=60,
                       overview_video_path=None, overview_every=3, overview_fps=30):
    """Generator: autonomously patrols both rooms, yielding (idx, rgb, wall)
    for each capture station. Transit-only waypoints are flown through but
    not yielded.

    If overview_video_path is given, a continuous third-person recording
    of the whole flight (not just onboard hover stills) is saved there —
    this is what actually shows the drone moving around the house.
    """
    first_wall = _wall_by_name(PATROL[0]["wall"])
    start_pos, start_yaw = _standoff_pose(first_wall)
    start_pos = start_pos + np.array([0.3, 0.3, 0.0])  # begin slightly off-station

    env = VisionCtrlAviary(
        img_res=IMG_RES,
        drone_model=DroneModel.CF2X,
        num_drones=1,
        initial_xyzs=start_pos.reshape(1, 3),
        initial_rpys=np.array([[0, 0, math.radians(start_yaw)]]),
        physics=Physics.PYB,
        pyb_freq=pyb_freq,
        ctrl_freq=ctrl_freq,
        gui=gui,
        user_debug_gui=False,
    )
    ctrl = DSLPIDControl(drone_model=DroneModel.CF2X)
    obs, _ = env.reset()
    build_house(env.CLIENT)  # must come after reset(), which wipes the scene
    control_timestep = 1.0 / ctrl_freq

    overview_writer = None
    if overview_video_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        overview_writer = cv2.VideoWriter(overview_video_path, fourcc, overview_fps, OVERVIEW_RES)
    step_counter = 0

    capture_idx = 0
    for step_spec in PATROL:
        if "wall" in step_spec:
            wall = _wall_by_name(step_spec["wall"])
            final_pos, final_yaw = _standoff_pose(wall)
        else:
            final_pos = np.array(step_spec["transit_pos"])
            final_yaw = step_spec["transit_yaw"]

        # DSLPIDControl is meant to track a smoothly-moving reference, not
        # jump to a far-off target held constant — feeding it a multi-meter
        # position error in one shot demands an unstable tilt command and
        # can flip this small, light (27g) drone. Interpolate the target
        # across approach_steps instead, matching how the library's own
        # trajectory-tracking examples drive it.
        start_pos = obs[0][0:3].copy()
        start_yaw = math.degrees(p.getEulerFromQuaternion(obs[0][3:7])[2])
        yaw_delta = ((final_yaw - start_yaw + 180) % 360) - 180

        ctrl.reset()
        n_steps = approach_steps + (hover_steps if step_spec["capture"] else 0)
        for i in range(n_steps):
            t = min(1.0, (i + 1) / approach_steps)
            interp_pos = start_pos + (final_pos - start_pos) * t
            interp_yaw = start_yaw + yaw_delta * t
            state = obs[0]
            action, _, _ = ctrl.computeControlFromState(
                control_timestep=control_timestep,
                state=state,
                target_pos=interp_pos,
                target_rpy=np.array([0, 0, math.radians(interp_yaw)]),
            )
            obs, _, _, _, _ = env.step(action.reshape(1, 4))

            step_counter += 1
            if overview_writer is not None and step_counter % overview_every == 0:
                cur_pos, cur_quat = obs[0][0:3], obs[0][3:7]
                frame = _capture_overview(env.CLIENT, cur_pos, cur_quat)
                overview_writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

        if step_spec["capture"]:
            capture_idx += 1
            rgb, _, _ = env._getDroneImages(0, segmentation=False)
            rgb = rgb[:, :, :3].astype(np.uint8)
            yield capture_idx, rgb, wall

    if overview_writer is not None:
        overview_writer.release()
    env.close()


if __name__ == "__main__":
    import cv2

    for idx, rgb, wall in fly_house_mission(gui=False):
        out_path = os.path.join(CAPTURE_DIR, f"house_frame_{idx:02d}_{wall['label']}_{wall['name']}.png")
        cv2.imwrite(out_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        print(f"[{idx}] {wall['name']:14s} label={wall['label']:6s} -> {out_path}")
    print("House patrol complete.")
