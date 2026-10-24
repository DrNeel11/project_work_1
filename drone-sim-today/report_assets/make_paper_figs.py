# -*- coding: utf-8 -*-
"""Small, single-column figures (8.6 cm wide) for the IEEE-format paper.
Run from drone-sim-today/ after experiments/analyze_scaleup.py."""
import json
import os
import sys

os.environ["UWTIG_YARD"] = "large"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = os.path.join(HERE, "paper_figs")
os.makedirs(OUT, exist_ok=True)
import geometry as geo  # noqa: E402
from planning.viewpoints import build_viewpoints  # noqa: E402
from sim_house import WALL_SEGMENTS  # noqa: E402

plt.rcParams.update({"font.family": "serif", "font.size": 7.5, "axes.linewidth": 0.6})
BLUE, GREY, RED = "#1f3a5f", "#777777", "#a61c1c"
SC = json.load(open(os.path.join(ROOT, "results", "scaleup_summary.json")))
W = 3.45  # inches, one IEEE column


def loop():
    fig, ax = plt.subplots(figsize=(W, 1.75))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    boxes = {"plan": (0.2, 3.0, "Planner\n(54/186 views)"), "cam": (3.7, 3.0, "Camera\nrender"), "det": (7.2, 3.0, "YOLO +\nuncertainty"),
             "loc": (7.2, 0.4, "Ray-cast to\nwall plane"), "mem": (3.7, 0.4, "Defect memory\n(identity, growth)"), "rep": (0.2, 0.4, "Report\n(wall, class)")}
    for k, (x, y, t) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), 2.6, 1.5, boxstyle="round,pad=0.04", fc="white", ec=BLUE, lw=0.8))
        ax.text(x + 1.3, y + 0.75, t, ha="center", va="center", fontsize=6.8)

    def arr(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=0.8, color=BLUE))
    arr(2.8, 3.75, 3.65, 3.75)
    arr(6.3, 3.75, 7.15, 3.75)
    arr(8.5, 3.0, 8.5, 1.95)
    arr(7.15, 1.15, 6.35, 1.15)
    arr(3.65, 1.15, 2.85, 1.15)
    arr(4.9, 1.95, 1.9, 2.95)
    ax.text(3.6, 2.45, "uncertainty, growth,\nstaleness prior", fontsize=6, color=RED, ha="center")
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(OUT, "loop.png"), dpi=300)
    plt.close(fig)


def yard():
    vps, _ = build_viewpoints(WALL_SEGMENTS)
    fig, ax = plt.subplots(figsize=(W, 2.75))
    for w in WALL_SEGMENTS:
        pt, n, u, _v = geo.wall_plane(w)
        hw = w["width"] / 2
        a, b = pt[:2] - u[:2] * hw, pt[:2] + u[:2] * hw
        ax.plot([a[0], b[0]], [a[1], b[1]], color=BLUE, lw=1.8, solid_capstyle="butt")
    for v in vps:
        ax.plot(v.pos[0], v.pos[1], ".", ms=1.4, color="#c0392b" if v.standoff < 2.0 else "#e59866")
    ax.add_patch(Rectangle((6.5, 3.6), 1.0, 0.8, fc="#cccccc", ec=GREY, lw=0.5, zorder=0))
    ax.add_patch(plt.Circle((-5.0, 3.0), 0.45, fc="#cccccc", ec=GREY, lw=0.5, zorder=0))
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_xlim(-17, 19)
    ax.set_ylim(-13, 16)
    ax.grid(alpha=0.2, lw=0.4)
    fig.tight_layout(pad=0.3)
    fig.savefig(os.path.join(OUT, "yard.png"), dpi=300)
    plt.close(fig)


def scatter():
    lab = {"uwtig": "UW-TIG", "ruckin_ipp": "Rückin", "alamdari_latency": "Alamdari", "gatsbi_gtsp": "GATSBI", "random": "Random",
           "bircher_rhnbv": "Bircher", "isler_nbv": "Isler"}
    fig, ax = plt.subplots(figsize=(W, 2.3))
    for p, name in lab.items():
        d = SC["large_old"]["planners"][p]
        ax.errorbar(d["total_flight_dist_m"], d["f1_confirmed"], yerr=[[d["f1_confirmed"] - d["f1_ci"][0]], [d["f1_ci"][1] - d["f1_confirmed"]]],
                    fmt="o", ms=4, color=RED if p == "uwtig" else BLUE, capsize=1.5, lw=0.7)
        pos = {"uwtig": (0.80, 0.030, "right"), "gatsbi_gtsp": (0.80, -0.045, "right"), "alamdari_latency": (1.0, 0.030, "center"),
               "ruckin_ipp": (1.0, -0.045, "center"), "random": (0.9, 0.012, "right")}
        dx, dy, ha = pos.get(p, (1.12, 0.012, "left"))
        ax.text(d["total_flight_dist_m"] * dx, d["f1_confirmed"] + dy, name, fontsize=6.5, ha=ha,
                color=RED if p == "uwtig" else "black", weight="bold" if p == "uwtig" else "normal")
    ax.set_xscale("log")
    ax.set_xticks([200, 500, 1000, 2000])
    ax.set_xticklabels(["200", "500", "1000", "2000"])
    ax.minorticks_off()
    ax.set_xlabel("Flight distance over three missions (m, log scale)")
    ax.set_ylabel("F1 (confirmed)")
    ax.set_ylim(0.35, 1.0)
    ax.grid(alpha=0.25, lw=0.4)
    fig.tight_layout(pad=0.3)
    fig.savefig(os.path.join(OUT, "scatter.png"), dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    loop()
    yard()
    scatter()
    print("paper figures written")
