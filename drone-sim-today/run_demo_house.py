"""Primary house-inspection demo: autonomous two-room patrol via
sim_house.py (gym-pybullet-drones physics/PID flight) + onboard sensor
detection (detect.py), saved as an annotated video.
"""
import argparse
import os

import cv2

from detect import detect_defects
from run_demo import OUTPUT_DIR, annotate
from sim_house import CAPTURE_DIR, fly_house_mission


def main(show_live=True, gui_sim=False, hold_frames=40):
    writer = None
    video_path = os.path.join(OUTPUT_DIR, "inspection_run_house.mp4")
    flythrough_path = os.path.join(OUTPUT_DIR, "house_flythrough.mp4")

    for idx, rgb, wall in fly_house_mission(gui=gui_sim, overview_video_path=flythrough_path):
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        dets = detect_defects(bgr)
        annotated = annotate(bgr, wall["label"], dets)

        if writer is None:
            h, w = annotated.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(video_path, fourcc, 5, (w, h))

        raw_path = os.path.join(CAPTURE_DIR, f"house_frame_{idx:02d}_{wall['label']}_{wall['name']}.png")
        cv2.imwrite(raw_path, bgr)
        annotated_path = os.path.join(OUTPUT_DIR, f"house_annotated_{idx:02d}_{wall['label']}_{wall['name']}.png")
        cv2.imwrite(annotated_path, annotated)

        for _ in range(hold_frames):
            writer.write(annotated)
            if show_live:
                cv2.imshow("Autonomous house inspection", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        found = [f"{d['label']}({d['confidence']:.2f})" for d in dets]
        print(f"[{wall['name']:14s}] ground_truth={wall['label']:5s} sensor={found if found else 'clear'}")

    if writer is not None:
        writer.release()
    if show_live:
        cv2.destroyAllWindows()
    print(f"Saved annotated video -> {video_path}")
    print(f"Saved third-person flythrough -> {flythrough_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-live", action="store_true", help="skip the live cv2 window")
    parser.add_argument("--gui-sim", action="store_true", help="also show the PyBullet 3D physics GUI window")
    args = parser.parse_args()
    main(show_live=not args.no_live, gui_sim=args.gui_sim)
