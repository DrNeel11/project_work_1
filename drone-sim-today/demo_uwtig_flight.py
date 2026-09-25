"""Flagship demo: real PID-controlled physics flight (not kinematic teleport,
not a fixed patrol list) driven live by the UW-TIG planner + trained
perception model + persistent memory, across a short sequence of missions.
This is the literal "detect -> assess uncertainty -> reinspect" closed loop
the proposal's Oct milestone calls for, visualized as an annotated video --
the qualitative complement to experiments/evaluate.py's quantitative sweep.
"""
import argparse
import math
import os
import sys
import tempfile

import cv2
import numpy as np
import pybullet as p

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geometry as geo  # noqa: E402
from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl  # noqa: E402
from gym_pybullet_drones.utils.enums import DroneModel, Physics  # noqa: E402
from memory.store import MemoryStore  # noqa: E402
from planning.planners import MissionBelief, UWTIGPlanner  # noqa: E402
from planning.viewpoints import build_viewpoints, cell_index_for_world_point  # noqa: E402
from scene.environment import retexture_ground  # noqa: E402
from sim_gpd import VisionCtrlAviary  # noqa: E402
from sim_house import FLIGHT_Z, IMG_RES, WALL_SEGMENTS, build_house  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OVERVIEW_RES = (480, 360)
COLORS = {"crack": (0, 0, 255), "corrosion": (0, 140, 255), "rust": (0, 140, 255),
          "leakage": (255, 140, 0), "leak": (255, 140, 0)}


class LiveHouseAdapter:
    """Lets experiments/scenarios.py's Scenario.setup_mission() (written
    against KinematicHouse) drive wall textures on the real flight env's
    already-built PyBullet bodies -- same call shape, no scenario code
    duplicated between the fast sim and the real-physics flagship demo."""

    def __init__(self, client, wall_bodies):
        self.client = client
        self.wall_bodies = wall_bodies
        self.wall_by_name = {w["name"]: w for w in WALL_SEGMENTS}

    def set_wall_texture(self, wall_name, texture_path):
        tex_id = p.loadTexture(texture_path, physicsClientId=self.client)
        p.changeVisualShape(self.wall_bodies[wall_name], -1, textureUniqueId=tex_id,
                             physicsClientId=self.client)


class ChaseCam:
    """Third-person chase camera with exponential smoothing on eye/target,
    so it trails the drone with a bit of cinematic lag instead of snapping
    to the instantaneous pose every frame (jarring on sharp yaw changes
    between viewpoints)."""

    def __init__(self, alpha=0.88, distance=0.9, height=0.55, lookahead=0.35):
        self.alpha = alpha
        self.distance, self.height, self.lookahead = distance, height, lookahead
        self.eye, self.target = None, None

    def capture(self, client, pos, quat):
        rot_mat = np.array(p.getMatrixFromQuaternion(quat)).reshape(3, 3)
        forward = rot_mat @ np.array([1.0, 0.0, 0.0])
        raw_eye = pos - forward * self.distance + np.array([0, 0, self.height])
        raw_target = pos + forward * self.lookahead

        if self.eye is None:
            self.eye, self.target = raw_eye, raw_target
        else:
            self.eye = self.alpha * self.eye + (1 - self.alpha) * raw_eye
            self.target = self.alpha * self.target + (1 - self.alpha) * raw_target

        view = p.computeViewMatrix(cameraEyePosition=self.eye, cameraTargetPosition=self.target,
                                    cameraUpVector=[0, 0, 1])
        proj = p.computeProjectionMatrixFOV(fov=70, aspect=OVERVIEW_RES[0] / OVERVIEW_RES[1],
                                             nearVal=0.05, farVal=30)
        _, _, rgba, _, _ = p.getCameraImage(OVERVIEW_RES[0], OVERVIEW_RES[1], view, proj, physicsClientId=client)
        return np.reshape(rgba, (OVERVIEW_RES[1], OVERVIEW_RES[0], 4))[:, :, :3].astype(np.uint8)


def _establishing_shot(client, writer, frames=75):
    """A slow orbiting wide shot of the whole yard (house + pipe rack +
    truss tower) before the mission starts. The chase-cam that follows the
    drone during flight stays close and wall-facing the entire time (the
    house is a fully enclosed two-room structure, so the drone never gets
    a clear line of sight to the surrounding yard once flying) -- this is
    the only point in the video the environment dressing is actually
    visible, so it earns its keep here rather than as invisible set
    dressing during the flight itself."""
    for i in range(frames):
        t = i / frames
        angle = math.radians(200 + 50 * t)
        radius = 14 - 3 * t
        height = 9 - 3 * t
        eye = [radius * math.cos(angle), radius * math.sin(angle) + 1.5, height]
        target = [0, 1.5, 1.0]
        view = p.computeViewMatrix(cameraEyePosition=eye, cameraTargetPosition=target, cameraUpVector=[0, 0, 1])
        proj = p.computeProjectionMatrixFOV(fov=60, aspect=OVERVIEW_RES[0] / OVERVIEW_RES[1],
                                             nearVal=0.1, farVal=60)
        _, _, rgba, _, _ = p.getCameraImage(OVERVIEW_RES[0], OVERVIEW_RES[1], view, proj,
                                             shadow=1, lightDirection=[0.6, -0.4, 1.0],
                                             renderer=p.ER_TINY_RENDERER, physicsClientId=client)
        frame = np.reshape(rgba, (OVERVIEW_RES[1], OVERVIEW_RES[0], 4))[:, :, :3].astype(np.uint8)
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))


def _smoothstep(t):
    """Ease-in-ease-out: zero velocity at both ends of the ramp, instead of
    the instant-full-speed/instant-stop a linear ramp gives DSLPIDControl's
    moving-reference tracking -- this is most of what "jerky" flight is."""
    return t * t * (3 - 2 * t)


def _annotate(frame_bgr, wall_name, dets, tag):
    out = frame_bgr.copy()
    for d in dets:
        x, y, w, h = d["bbox"]
        color = COLORS.get(d["label"], (0, 255, 0))
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        text = f"{d['label']} c={d['confidence']:.2f} u={d['uncertainty']:.2f}"
        cv2.putText(out, text, (x, max(0, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
    label = f"{tag} | wall: {wall_name}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(out, (6, 6), (14 + tw, 20 + th), (0, 0, 0), -1)
    cv2.putText(out, label, (10, 20 + th - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return out


def _fly_to(env, ctrl, obs, target_pos, target_yaw, control_timestep, approach_steps,
            hover_steps, chase_cam=None, overview_writer=None, overview_every=3, step_counter=0):
    start_pos = obs[0][0:3].copy()
    start_yaw = math.degrees(p.getEulerFromQuaternion(obs[0][3:7])[2])
    yaw_delta = ((target_yaw - start_yaw + 180) % 360) - 180
    ctrl.reset()
    for i in range(approach_steps + hover_steps):
        t_linear = min(1.0, (i + 1) / approach_steps)
        t = _smoothstep(t_linear)
        interp_pos = start_pos + (target_pos - start_pos) * t
        interp_yaw = start_yaw + yaw_delta * t
        action, _, _ = ctrl.computeControlFromState(
            control_timestep=control_timestep, state=obs[0],
            target_pos=interp_pos, target_rpy=np.array([0, 0, math.radians(interp_yaw)]))
        obs, _, _, _, _ = env.step(action.reshape(1, 4))
        step_counter += 1
        if overview_writer is not None and step_counter % overview_every == 0:
            frame = chase_cam.capture(env.CLIENT, obs[0][0:3], obs[0][3:7])
            overview_writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    return obs, step_counter


def run(n_missions=3, budget_per_mission=8, gui=False, ctrl_freq=48, pyb_freq=240,
        approach_steps=300, hover_steps=40, scenario_name="multi_defect"):
    from experiments.scenarios import SCENARIO_REGISTRY
    from perception.ml_detector import detect_with_uncertainty as detector

    # "growing" uses a procedurally-rendered texture the real photo-trained
    # detector doesn't recognize (see RESULTS.md limitations) -- the
    # flagship demo instead uses real MBDD2025 photos (multi_defect) so it
    # actually shows the trained model detecting something.
    scenario = SCENARIO_REGISTRY[scenario_name](seed=7)
    wall_names = [w["name"] for w in WALL_SEGMENTS]
    viewpoints, dist = build_viewpoints(WALL_SEGMENTS)
    rng = np.random.RandomState(7)
    planner = UWTIGPlanner(viewpoints, dist, rng)

    first = viewpoints[0]
    env = VisionCtrlAviary(
        img_res=np.array(IMG_RES), drone_model=DroneModel.CF2X, num_drones=1,
        initial_xyzs=(first.pos + np.array([0.3, 0.3, 0.0])).reshape(1, 3),
        initial_rpys=np.array([[0, 0, math.radians(first.yaw_deg)]]),
        physics=Physics.PYB, pyb_freq=pyb_freq, ctrl_freq=ctrl_freq, gui=gui, user_debug_gui=False,
    )
    ctrl = DSLPIDControl(drone_model=DroneModel.CF2X)
    obs, _ = env.reset()
    wall_bodies = build_house(env.CLIENT)
    retexture_ground(env.CLIENT, env.PLANE_ID)
    house = LiveHouseAdapter(env.CLIENT, wall_bodies)
    control_timestep = 1.0 / ctrl_freq

    flythrough_path = os.path.join(OUTPUT_DIR, "uwtig_flythrough.mp4")
    inspection_path = os.path.join(OUTPUT_DIR, "uwtig_inspection.mp4")
    overview_writer = cv2.VideoWriter(flythrough_path, cv2.VideoWriter_fourcc(*"mp4v"), 30, OVERVIEW_RES)
    _establishing_shot(env.CLIENT, overview_writer)
    chase_cam = ChaseCam()
    inspect_writer = None
    step_counter = 0

    belief = MissionBelief(wall_names)
    with MemoryStore() as mem, tempfile.TemporaryDirectory() as tmp_dir:
        for mission_index in range(1, n_missions + 1):
            gt = scenario.setup_mission(house, mission_index, tmp_dir)
            mission_id = mem.create_mission(scenario.name, "uwtig", seed=7, mission_index=mission_index)
            if mission_index > 1:
                priors = {}
                for wall in wall_names:
                    wd = house.wall_by_name[wall]
                    for d in mem.active_defects_on_wall(wall):
                        hist = mem.get_defect_history(d["id"])
                        if not hist:
                            continue
                        cell = cell_index_for_world_point(wd, (d["world_x"], d["world_y"], d["world_z"]))
                        priors[(wall, cell)] = (hist[-1]["uncertainty"], max(0.0, mem.compute_growth(d["id"])))
                belief.seed_temporal_priors(priors)

            current_id = None
            print(f"\n=== mission {mission_index}: ground truth {gt} ===")
            for step_i in range(budget_per_mission):
                vp = planner.select_next(belief, current_id)
                obs, step_counter = _fly_to(env, ctrl, obs, vp.pos, vp.yaw_deg, control_timestep,
                                             approach_steps, hover_steps, chase_cam=chase_cam,
                                             overview_writer=overview_writer, step_counter=step_counter)
                current_id = vp.id

                rgb, _, _ = env._getDroneImages(0, segmentation=False)
                bgr = cv2.cvtColor(rgb[:, :, :3].astype(np.uint8), cv2.COLOR_RGB2BGR)
                drone_pos, drone_quat = obs[0][0:3], obs[0][3:7]
                wall_dict = house.wall_by_name[vp.wall]
                dets = detector(bgr)

                for det in dets:
                    x, y, w, h = det["bbox"]
                    world_xyz = geo.localize_on_wall((x + w / 2, y + h / 2), drone_pos, drone_quat,
                                                       wall_dict, IMG_RES[0], IMG_RES[1])
                    if world_xyz is None:
                        continue
                    corners = [geo.localize_on_wall((x, y), drone_pos, drone_quat, wall_dict, IMG_RES[0], IMG_RES[1]),
                               geo.localize_on_wall((x + w, y + h), drone_pos, drone_quat, wall_dict, IMG_RES[0], IMG_RES[1])]
                    corners = [c for c in corners if c is not None]
                    size_m = float(np.linalg.norm(corners[0] - corners[1])) if len(corners) == 2 else 0.0

                    crop = bgr[max(0, y):y + h, max(0, x):x + w]
                    _, _, _, growth = mem.match_or_create_defect(
                        mission_id, vp.wall, det["label"], det["confidence"], det["uncertainty"],
                        (x, y, w, h), tuple(world_xyz), size_m=size_m, crop_bgr=crop)
                    belief.record_detection(vp.wall, world_xyz, det["uncertainty"], growth, wall_dict)

                belief.record_visit(vp)
                tag = f"mission {mission_index} step {step_i} | budget {budget_per_mission}"
                annotated = _annotate(bgr, vp.wall, dets, tag)
                if inspect_writer is None:
                    h, w = annotated.shape[:2]
                    inspect_writer = cv2.VideoWriter(inspection_path, cv2.VideoWriter_fourcc(*"mp4v"), 4, (w, h))
                for _ in range(12):
                    inspect_writer.write(annotated)

                found = [f"{d['label']}(c={d['confidence']:.2f},u={d['uncertainty']:.2f})" for d in dets]
                print(f"  [{vp.id}] -> {found if found else 'clear'}")

    overview_writer.release()
    if inspect_writer is not None:
        inspect_writer.release()
    env.close()
    print(f"\nSaved -> {flythrough_path}\nSaved -> {inspection_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--missions", type=int, default=3)
    ap.add_argument("--budget", type=int, default=8)
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--scenario", default="multi_defect",
                     choices=["static", "uncertain", "growing", "multi_defect"])
    args = ap.parse_args()
    run(n_missions=args.missions, budget_per_mission=args.budget, gui=args.gui,
        scenario_name=args.scenario)
