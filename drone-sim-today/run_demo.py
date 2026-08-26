"""Ties the autonomous flight sim + onboard detection together:
runs the full waypoint mission, overlays detection boxes on each captured
frame, shows a live window, and saves an annotated video of the run.
"""
import argparse
import os

import cv2

from detect import detect_defects
from sim import CAPTURE_DIR, fly_mission

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

COLORS = {"crack": (0, 0, 255), "rust": (0, 140, 255), "leak": (255, 140, 0)}


def annotate(frame_bgr, wall_label, detections):
    out = frame_bgr.copy()
    for d in detections:
        x, y, w, h = d["bbox"]
        color = COLORS.get(d["label"], (0, 255, 0))
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        text = f"{d['label']} {d['confidence']:.2f}"
        cv2.putText(out, text, (x, max(0, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    tag = "DEFECT" if detections else "clear"
    label = f"ground truth: {wall_label} | sensor: {tag}"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(out, (6, 6), (14 + tw, 20 + th), (0, 0, 0), -1)
    cv2.putText(out, label, (10, 20 + th - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return out


def main(show_live=True, gui_sim=False, hold_frames=40):
    frame_h, frame_w = None, None
    writer = None
    video_path = os.path.join(OUTPUT_DIR, "inspection_run.mp4")

    for idx, rgb, wall in fly_mission(gui=gui_sim):
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        dets = detect_defects(bgr)
        annotated = annotate(bgr, wall["label"], dets)

        if writer is None:
            frame_h, frame_w = annotated.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(video_path, fourcc, 5, (frame_w, frame_h))

        raw_path = os.path.join(CAPTURE_DIR, f"frame_{idx:02d}_{wall['label']}.png")
        cv2.imwrite(raw_path, bgr)
        annotated_path = os.path.join(OUTPUT_DIR, f"annotated_{idx:02d}_{wall['label']}.png")
        cv2.imwrite(annotated_path, annotated)

        for _ in range(hold_frames):
            writer.write(annotated)
            if show_live:
                cv2.imshow("Drone inspection feed", annotated)
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
    parser.add_argument("--gui-sim", action="store_true", help="also show the PyBullet 3D GUI window")
    args = parser.parse_args()
    main(show_live=not args.no_live, gui_sim=args.gui_sim)
