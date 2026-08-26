"""Primary demo entry point: autonomous PID-controlled flight via
gym-pybullet-drones (sim_gpd.py) + onboard sensor detection (detect.py),
saved as an annotated video. This is the "real" open-source autonomous
drone simulator version — see run_demo.py for the earlier scripted/
kinematic version kept for reference.
"""
import argparse
import os

import cv2

from detect import detect_defects
from run_demo import OUTPUT_DIR, annotate
from sim_gpd import fly_inspection_mission, CAPTURE_DIR


def main(show_live=True, gui_sim=False, hold_frames=40):
    writer = None
    video_path = os.path.join(OUTPUT_DIR, "inspection_run_gpd.mp4")

    for idx, rgb, wall in fly_inspection_mission(gui=gui_sim):
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        dets = detect_defects(bgr)
        annotated = annotate(bgr, wall["label"], dets)

        if writer is None:
            h, w = annotated.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(video_path, fourcc, 5, (w, h))

        raw_path = os.path.join(CAPTURE_DIR, f"gpd_frame_{idx:02d}_{wall['label']}.png")
        cv2.imwrite(raw_path, bgr)
        annotated_path = os.path.join(OUTPUT_DIR, f"gpd_annotated_{idx:02d}_{wall['label']}.png")
        cv2.imwrite(annotated_path, annotated)

        for _ in range(hold_frames):
            writer.write(annotated)
            if show_live:
                cv2.imshow("Autonomous drone inspection (gym-pybullet-drones)", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        found = [f"{d['label']}({d['confidence']:.2f})" for d in dets]
        print(f"[wall {idx}] ground_truth={wall['label']:5s} sensor={found if found else 'clear'}")

    if writer is not None:
        writer.release()
    if show_live:
        cv2.destroyAllWindows()
    print(f"Saved annotated video -> {video_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-live", action="store_true", help="skip the live cv2 window")
    parser.add_argument("--gui-sim", action="store_true", help="also show the PyBullet 3D physics GUI window")
    args = parser.parse_args()
    main(show_live=not args.no_live, gui_sim=args.gui_sim)
