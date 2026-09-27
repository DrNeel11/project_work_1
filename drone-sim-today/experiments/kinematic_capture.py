"""Fast headless capture for the planner comparison: teleports a virtual
camera to a candidate Viewpoint and renders, with no PID flight physics
stepping (detection/planning quality doesn't depend on flight dynamics --
see the flagship demo_uwtig_flight.py for the real-physics version).
Reuses sim_house.build_house() directly on a bare DIRECT client and
geometry.py's camera convention so localization math stays identical
between this and the trained-perception/real-flight paths.
"""
import math
import os
import sys

import numpy as np
import pybullet as p
import pybullet_data

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geometry as geo  # noqa: E402
from scene.environment import retexture_ground  # noqa: E402
from sim_house import IMG_RES, WALL_SEGMENTS, build_house  # noqa: E402


class KinematicHouse:
    def __init__(self, gui=False):
        self.client = p.connect(p.GUI if gui else p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.client)
        plane_id = p.loadURDF("plane.urdf", physicsClientId=self.client)
        retexture_ground(self.client, plane_id)
        self.wall_bodies = build_house(self.client)  # {wall_name: body_id}
        self.wall_by_name = {w["name"]: w for w in WALL_SEGMENTS}

    def set_wall_texture(self, wall_name, texture_path):
        tex_id = p.loadTexture(texture_path, physicsClientId=self.client)
        p.changeVisualShape(self.wall_bodies[wall_name], -1, textureUniqueId=tex_id,
                             physicsClientId=self.client)

    def capture(self, viewpoint):
        """Returns (bgr_uint8, drone_pos, drone_quat) at the given Viewpoint."""
        quat = p.getQuaternionFromEuler([0, 0, math.radians(viewpoint.yaw_deg)])
        view, proj = geo.drone_camera_matrices(viewpoint.pos, quat)
        view_flat = view.flatten(order="F").tolist()
        proj_flat = proj.flatten(order="F").tolist()
        _, _, rgba, _, _ = p.getCameraImage(
            width=int(IMG_RES[0]), height=int(IMG_RES[1]),
            viewMatrix=view_flat, projectionMatrix=proj_flat,
            shadow=1, lightDirection=[0.6, -0.4, 1.0],
            renderer=p.ER_TINY_RENDERER, physicsClientId=self.client,
        )
        rgb = np.reshape(rgba, (int(IMG_RES[1]), int(IMG_RES[0]), 4))[:, :, :3].astype(np.uint8)
        bgr = rgb[:, :, ::-1].copy()
        return bgr, viewpoint.pos, quat

    def close(self):
        p.disconnect(physicsClientId=self.client)


if __name__ == "__main__":
    import cv2

    from planning.viewpoints import build_viewpoints

    house = KinematicHouse()
    vps, _ = build_viewpoints(WALL_SEGMENTS)
    v = next(v for v in vps if v.wall == "A-west")
    bgr, pos, quat = house.capture(v)
    out = os.path.join(os.path.dirname(__file__), "_kinematic_preview.png")
    cv2.imwrite(out, bgr)
    print("wrote", out, "viewpoint", v.id)
    house.close()
