"""Real-hardware counterpart to sim_house.py, for a DJI Tello.

UNTESTED — written without physical hardware to verify against. Treat as
a conservative starting point: read every step before running it, keep
prop guards on, fly somewhere open and low first, and be ready to hit
the emergency stop (Tello.emergency()) if anything looks wrong.

Unlike the simulator, the Tello's own onboard flight controller handles
stabilization — we only send it relative move/rotate commands, not RPMs.
There is no absolute position feedback here (no RTK/UWB/mocap), so drift
accumulates over the route; recalibrate the move distances against your
actual room before trusting this to fly a full patrol unattended.
"""
import argparse
import os
import time

import cv2
from djitellopy import Tello

from detect import detect_defects

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Each leg: rotate first (degrees, +ccw/-cw per djitellopy convention),
# then move forward (cm). "capture" walls get a photo + detection pass.
# These numbers are placeholders — measure your actual room and replace
# them before flying a real patrol.
PATROL = [
    {"rotate": 0, "forward": 100, "label": "wall-1", "capture": True},
    {"rotate": 90, "forward": 100, "label": "wall-2", "capture": True},
    {"rotate": 90, "forward": 100, "label": "wall-3", "capture": True},
    {"rotate": 90, "forward": 100, "label": "wall-4", "capture": True},
]

MIN_MOVE_CM = 20  # Tello rejects move commands smaller than this


def run(dry_run=True):
    tello = Tello()
    tello.connect()
    print(f"battery: {tello.get_battery()}%")
    if tello.get_battery() < 30:
        raise RuntimeError("battery too low to fly safely — charge before continuing")

    tello.streamon()
    frame_reader = tello.get_frame_read()
    time.sleep(1)  # let the video stream warm up

    if dry_run:
        print("dry_run=True: connected + video stream OK, not taking off. "
              "Pass dry_run=False once you've verified this on the ground.")
        tello.streamoff()
        return

    tello.takeoff()
    time.sleep(1)

    try:
        for i, leg in enumerate(PATROL, start=1):
            if leg["rotate"] > 0:
                tello.rotate_clockwise(leg["rotate"])
            elif leg["rotate"] < 0:
                tello.rotate_counter_clockwise(-leg["rotate"])
            if leg["forward"] >= MIN_MOVE_CM:
                tello.move_forward(leg["forward"])
            time.sleep(1)  # settle before capturing

            if leg["capture"]:
                frame = frame_reader.frame  # RGB
                bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                dets = detect_defects(bgr)
                labels = [f"{d['label']}({d['confidence']:.2f})" for d in dets]
                print(f"[{i}] {leg['label']}: {labels if labels else 'clear'}")
                out_path = os.path.join(OUTPUT_DIR, f"tello_{i:02d}_{leg['label']}.png")
                cv2.imwrite(out_path, bgr)
    finally:
        # Always try to land, even if a leg raised an exception.
        tello.land()
        tello.streamoff()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fly", action="store_true",
                         help="actually take off and fly the patrol (default is a safe connection-only dry run)")
    args = parser.parse_args()
    run(dry_run=not args.fly)
