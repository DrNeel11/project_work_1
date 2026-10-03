"""Splices two or three of demo_uwtig_flight.py's per-planner flythrough (or
inspection) videos into one side-by-side comparison video, so the effect of
the novel planner is directly watchable rather than only visible in a CSV.

Each per-planner video already has its planner name burned into the corner
(demo_uwtig_flight.py's _label_frame) and is produced from the identical
scenario/seed/budget/missions, so frame counts match exactly (both the
chase-cam flythrough and the onboard inspection video are driven by fixed
step counts that don't depend on which planner is flying) -- this script
does a direct frame-by-frame horizontal concatenation, not any alignment
or resampling logic.

Usage:
    python make_comparison_video.py --kind flythrough --planners uwtig isler_nbv
    python make_comparison_video.py --kind inspection --planners uwtig isler_nbv random
"""
import argparse
import os

import cv2

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def make_comparison(kind, planners, out_path):
    paths = [os.path.join(OUTPUT_DIR, f"{p}_{kind}.mp4") for p in planners]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(f"missing video(s), run demo_uwtig_flight.py --planner first: {missing}")

    caps = [cv2.VideoCapture(p) for p in paths]
    fps = caps[0].get(cv2.CAP_PROP_FPS) or 30
    w = int(caps[0].get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(caps[0].get(cv2.CAP_PROP_FRAME_HEIGHT))
    counts = [int(c.get(cv2.CAP_PROP_FRAME_COUNT)) for c in caps]
    n_frames = min(counts)
    if len(set(counts)) > 1:
        print(f"note: frame counts differ {dict(zip(planners, counts))} -- using shortest ({n_frames})")

    writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w * len(planners), h))
    for _ in range(n_frames):
        frames = []
        ok_all = True
        for cap in caps:
            ok, frame = cap.read()
            ok_all = ok_all and ok
            frames.append(frame if ok else None)
        if not ok_all:
            break
        writer.write(cv2.hconcat(frames))
    writer.release()
    for cap in caps:
        cap.release()
    print(f"wrote {out_path} ({n_frames} frames, {w * len(planners)}x{h})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="flythrough", choices=["flythrough", "inspection"])
    ap.add_argument("--planners", nargs="+", default=["uwtig", "isler_nbv"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or os.path.join(OUTPUT_DIR, f"comparison_{args.kind}_{'_vs_'.join(args.planners)}.mp4")
    make_comparison(args.kind, args.planners, out)
