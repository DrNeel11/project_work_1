"""VisionCtrlAviary: a gym-pybullet-drones CtrlAviary with an onboard RGB
camera enabled. CtrlAviary's stock constructor hardcodes
vision_attributes=False, so this small subclass exists purely to flip that
on; sim_house.py and demo_uwtig_flight.py both build their real-physics
flight environments from it.
"""
import numpy as np

from gym_pybullet_drones.envs.BaseAviary import BaseAviary
from gym_pybullet_drones.envs.CtrlAviary import CtrlAviary

IMG_RES = np.array([320, 240])


class VisionCtrlAviary(CtrlAviary):
    """CtrlAviary with an onboard RGB camera enabled (not exposed by the
    stock CtrlAviary constructor, which hardcodes vision_attributes=False)."""

    def __init__(self, img_res=IMG_RES, **kwargs):
        kwargs.setdefault("obstacles", False)
        BaseAviary.__init__(self, vision_attributes=True, **kwargs)
        self.IMG_RES = np.array(img_res)
        self.rgb = np.zeros((self.NUM_DRONES, self.IMG_RES[1], self.IMG_RES[0], 4))
