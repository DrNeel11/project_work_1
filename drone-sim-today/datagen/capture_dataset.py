"""Renders (RGB, YOLO-seg polygon label) pairs for the synthetic defect
dataset. For each sample: generate a texture+label-mask pair (scene/texture_gen.py),
bind the texture to a single reusable wall quad in a headless PyBullet client,
render from a randomized standoff camera pose, then re-bind the label-mask
texture and re-render from the IDENTICAL camera pose with flat/unlit shading.
Thresholding the mask render by class color recovers a pixel-perfect
segmentation polygon for the photorealistic render, with no manual
annotation and no analytic UV math.
"""
import math
import os
import sys
import tempfile

import cv2
import numpy as np
import pybullet as p

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import geometry as geo  # noqa: E402
from scene import texture_gen  # noqa: E402

WALL_QUAD_OBJ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "scene", "wall_quad.obj")

WALL = dict(x=0.0, y=0.0, yaw=90.0, width=2.6, z_center=1.2)
WALL_HEIGHT = 2.4
IMG_RES = (320, 240)  # (w, h), matches sim_house.IMG_RES

STANDOFF_RANGE = (0.6, 1.9)
LATERAL_MARGIN = 0.4  # keep camera's lateral offset this far from the wall edge
VERTICAL_RANGE = (-0.5, 0.5)
YAW_JITTER_DEG = 18.0
ROLL_PITCH_JITTER_DEG = 6.0

MIN_CONTOUR_AREA_PX = 20
COLOR_TOL = 40  # per-channel tolerance when thresholding label-mask colors


class DatasetRig:
    """Owns one headless PyBullet client + one reusable wall body."""

    def __init__(self):
        self.client = p.connect(p.DIRECT)
        self._build()
        self._n_since_reset = 0

    def _build(self):
        p.resetSimulation(physicsClientId=self.client)
        self.vis_shape = p.createVisualShape(
            p.GEOM_MESH, fileName=WALL_QUAD_OBJ,
            meshScale=[WALL["width"] / 2, 1, WALL_HEIGHT / 2],
            rgbaColor=[1, 1, 1, 1], physicsClientId=self.client,
        )
        orn = p.getQuaternionFromEuler([0, 0, math.radians(WALL["yaw"])])
        self.body = p.createMultiBody(
            baseMass=0, baseVisualShapeIndex=self.vis_shape,
            basePosition=[WALL["x"], WALL["y"], WALL["z_center"]], baseOrientation=orn,
            physicsClientId=self.client,
        )

    def _maybe_recycle(self):
        # loadTexture'd textures aren't freed until resetSimulation; recycle
        # the client periodically so long dataset-gen runs don't grow unbounded.
        self._n_since_reset += 1
        if self._n_since_reset >= 200:
            self._build()
            self._n_since_reset = 0

    def _set_texture(self, pil_img, tmp_dir, name="tex"):
        path = os.path.join(tmp_dir, f"{name}_{id(pil_img)}.png")
        pil_img.save(path)
        tex_id = p.loadTexture(path, physicsClientId=self.client)
        p.changeVisualShape(self.body, -1, textureUniqueId=tex_id, physicsClientId=self.client)

    def _sample_camera_pose(self, rng):
        standoff = rng.uniform(*STANDOFF_RANGE)
        lat_max = max(0.05, WALL["width"] / 2 - LATERAL_MARGIN)
        lateral = rng.uniform(-lat_max, lat_max)
        vertical = rng.uniform(*VERTICAL_RANGE)
        yaw_jitter = rng.uniform(-YAW_JITTER_DEG, YAW_JITTER_DEG)
        roll = rng.uniform(-ROLL_PITCH_JITTER_DEG, ROLL_PITCH_JITTER_DEG)
        pitch = rng.uniform(-ROLL_PITCH_JITTER_DEG, ROLL_PITCH_JITTER_DEG)

        point, normal, u_axis, v_axis = geo.wall_plane(WALL)
        cam_pos = point + standoff * normal + lateral * u_axis + vertical * v_axis
        approach_yaw = WALL["yaw"] + 90 + yaw_jitter
        quat = p.getQuaternionFromEuler([math.radians(roll), math.radians(pitch), math.radians(approach_yaw)])
        return cam_pos, quat

    def render(self, cam_pos, quat, flat_shading):
        view, proj = geo.drone_camera_matrices(cam_pos, quat)
        view_flat = view.flatten(order="F").tolist()
        proj_flat = proj.flatten(order="F").tolist()
        kwargs = dict(width=IMG_RES[0], height=IMG_RES[1], viewMatrix=view_flat,
                      projectionMatrix=proj_flat, physicsClientId=self.client,
                      renderer=p.ER_TINY_RENDERER)
        if flat_shading:
            kwargs.update(shadow=0, lightAmbientCoeff=1.0, lightDiffuseCoeff=0.0,
                          lightSpecularCoeff=0.0, lightColor=[1, 1, 1])
        else:
            kwargs.update(shadow=1, lightDirection=[0.6, -0.4, 1.0])
        _, _, rgba, _, _ = p.getCameraImage(**kwargs)
        rgb = np.reshape(rgba, (IMG_RES[1], IMG_RES[0], 4))[:, :, :3].astype(np.uint8)
        return rgb

    def capture_sample(self, defect_type, rng, severity=1.0, center=None, base_color=None):
        """Returns (rgb_bgr, yolo_label_lines, meta)."""
        tex, mask, meta = texture_gen.make_wall_texture(
            defect_type, rng, severity=severity, base_color=base_color, center=center)
        cam_pos, quat = self._sample_camera_pose(rng)

        with tempfile.TemporaryDirectory() as tmp_dir:
            self._set_texture(tex, tmp_dir)
            rgb = self.render(cam_pos, quat, flat_shading=False)
            self._set_texture(mask, tmp_dir)
            mask_rgb = self.render(cam_pos, quat, flat_shading=True)
        self._maybe_recycle()

        labels = _mask_to_yolo_labels(mask_rgb, IMG_RES[0], IMG_RES[1])
        meta["cam_pos"] = cam_pos
        meta["cam_quat"] = quat
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), labels, meta

    def close(self):
        p.disconnect(physicsClientId=self.client)


def _mask_to_yolo_labels(mask_rgb, img_w, img_h):
    lines = []
    for label, color in texture_gen.LABEL_COLOR.items():
        lo = np.array([max(0, c - COLOR_TOL) for c in color])
        hi = np.array([min(255, c + COLOR_TOL) for c in color])
        bin_mask = cv2.inRange(mask_rgb, lo, hi)
        bin_mask = cv2.morphologyEx(bin_mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        class_id = texture_gen.CLASS_IDS[label]
        for c in contours:
            if cv2.contourArea(c) < MIN_CONTOUR_AREA_PX:
                continue
            pts = c.reshape(-1, 2).astype(np.float64)
            pts[:, 0] /= img_w
            pts[:, 1] /= img_h
            coords = " ".join(f"{v:.5f}" for v in pts.flatten())
            lines.append(f"{class_id} {coords}")
    return lines


if __name__ == "__main__":
    rig = DatasetRig()
    rng = np.random.RandomState(0)
    out = os.path.join(os.path.dirname(__file__), "_capture_preview")
    os.makedirs(out, exist_ok=True)
    for i, dtype in enumerate(["crack", "corrosion", "leakage", "clean"]):
        bgr, labels, meta = rig.capture_sample(dtype, rng)
        cv2.imwrite(os.path.join(out, f"{i}_{dtype}.png"), bgr)
        print(dtype, "labels:", len(labels), meta["defect_type"], meta.get("center"))
    rig.close()
    print("wrote previews to", out)
