"""Autonomous drone inspection flight using gym-pybullet-drones — a real
open-source autonomous drone simulator (Panerati et al., IROS 2021) with
actual rotor thrust/drag physics and closed-loop PID flight control
(DSLPIDControl), replacing the scripted kinematic teleport used in sim.py.

The drone autonomously flies a waypoint corridor past a row of textured
inspection walls; at each wall it hovers and its onboard FPV camera
captures a frame for the sensor pipeline in detect.py.
"""
import math
import os

import numpy as np
import pybullet as p

from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl
from gym_pybullet_drones.envs.BaseAviary import BaseAviary
from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary
from gym_pybullet_drones.utils.enums import DroneModel, Physics

SCENE_DIR = os.path.join(os.path.dirname(__file__), "scene")
CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "captures")
os.makedirs(CAPTURE_DIR, exist_ok=True)

WALL_QUAD_OBJ = os.path.join(SCENE_DIR, "wall_quad.obj")

# Small-scale corridor sized for a ~9cm CF2X quadrotor. Spacing must clear
# the visible width at the 0.8m standoff distance (~0.92m at 60deg FOV) or
# neighboring walls bleed into frame edges.
WALLS = [
    (-4.2, "clean_wall_1.png", "clean"),
    (-2.8, "crack_wall_1.png", "crack"),
    (-1.4, "clean_wall_2.png", "clean"),
    (0.0, "rust_wall_1.png", "rust"),
    (1.4, "crack_wall_2.png", "crack"),
    (2.8, "leak_wall_1.png", "leak"),
    (4.2, "clean_wall_3.png", "clean"),
]
WALL_Y = 0.8
WALL_Z = 0.3
FLIGHT_Y = 0.0
FLIGHT_Z = 0.3
IMG_RES = np.array([320, 240])
INIT_YAW = math.pi / 2  # body +x -> world +y, facing the wall row


class VisionCtrlAviary(CtrlAviary):
    """CtrlAviary with an onboard RGB camera enabled (not exposed by the
    stock CtrlAviary constructor, which hardcodes vision_attributes=False)."""

    def __init__(self, img_res=IMG_RES, **kwargs):
        kwargs.setdefault("obstacles", False)
        BaseAviary.__init__(self, vision_attributes=True, **kwargs)
        self.IMG_RES = np.array(img_res)
        self.rgb = np.zeros((self.NUM_DRONES, self.IMG_RES[1], self.IMG_RES[0], 4))


def build_scene(client):
    wall_infos = []
    for x, texture_file, label in WALLS:
        vis = p.createVisualShape(
            p.GEOM_MESH, fileName=WALL_QUAD_OBJ, meshScale=[0.3, 1, 0.35],
            rgbaColor=[1, 1, 1, 1], physicsClientId=client,
        )
        body = p.createMultiBody(
            baseMass=0, baseVisualShapeIndex=vis,
            basePosition=[x, WALL_Y, WALL_Z], physicsClientId=client,
        )
        tex_id = p.loadTexture(os.path.join(SCENE_DIR, texture_file), physicsClientId=client)
        p.changeVisualShape(body, -1, textureUniqueId=tex_id, physicsClientId=client)
        wall_infos.append({"body": body, "pos": (x, WALL_Y, WALL_Z), "label": label})
    return wall_infos


def fly_inspection_mission(gui=False, ctrl_freq=48, pyb_freq=240,
                            approach_steps=260, hover_steps=60):
    """Generator: autonomously flies to each wall waypoint using DSLPIDControl,
    hovers, captures an onboard camera frame, and yields (idx, rgb, wall_info)."""
    start_xyz = np.array([[WALLS[0][0] - 0.5, FLIGHT_Y, FLIGHT_Z]])
    init_rpy = np.array([[0, 0, INIT_YAW]])

    env = VisionCtrlAviary(
        drone_model=DroneModel.CF2X,
        num_drones=1,
        initial_xyzs=start_xyz,
        initial_rpys=init_rpy,
        physics=Physics.PYB,
        pyb_freq=pyb_freq,
        ctrl_freq=ctrl_freq,
        gui=gui,
        user_debug_gui=False,
    )
    ctrl = DSLPIDControl(drone_model=DroneModel.CF2X)

    obs, _ = env.reset()
    # reset() calls p.resetSimulation() internally, so the scene must be
    # (re)built *after* reset, not before, or it gets wiped out.
    walls = build_scene(env.CLIENT)
    control_timestep = 1.0 / ctrl_freq

    for idx, wall in enumerate(walls, start=1):
        target_pos = np.array([wall["pos"][0], FLIGHT_Y, FLIGHT_Z])
        for _ in range(approach_steps + hover_steps):
            state = obs[0]
            action, _, _ = ctrl.computeControlFromState(
                control_timestep=control_timestep,
                state=state,
                target_pos=target_pos,
                target_rpy=np.array([0, 0, INIT_YAW]),
            )
            obs, _, _, _, _ = env.step(action.reshape(1, 4))

        rgb, _, _ = env._getDroneImages(0, segmentation=False)
        rgb = rgb[:, :, :3].astype(np.uint8)
        yield idx, rgb, wall

    env.close()


if __name__ == "__main__":
    import cv2

    for idx, rgb, wall in fly_inspection_mission(gui=False):
        out_path = os.path.join(CAPTURE_DIR, f"gpd_frame_{idx:02d}_{wall['label']}.png")
        cv2.imwrite(out_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        print(f"[{idx}] wall x={wall['pos'][0]} label={wall['label']} -> {out_path}")
    print("Mission complete.")
