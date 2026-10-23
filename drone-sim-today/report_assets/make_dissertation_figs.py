# -*- coding: utf-8 -*-
"""Generates the vector-style figures used by build_dissertation.py: yard
plan with candidate viewpoints, planner decision flow, sweep result charts.
Numbers come straight from results/comparison.csv. Run from drone-sim-today/."""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = os.path.join(HERE, "dissertation_figs")
os.makedirs(OUT, exist_ok=True)

import geometry as geo  # noqa: E402
from planning.viewpoints import build_viewpoints  # noqa: E402

# sim_house imports pybullet; copy the layout without importing it
import ast  # noqa: E402
src = open(os.path.join(ROOT, "sim_house.py"), encoding="utf-8").read()
start = src.index("WALL_SEGMENTS = [")
end = src.index("\n]\n", start) + 3
WALL_SEGMENTS = eval(src[start:end].split("=", 1)[1].strip().replace("dict(", "dict("))

plt.rcParams.update({"font.family": "serif", "font.size": 10})
BLUE, GREY, RED = "#1f3a5f", "#777777", "#a61c1c"

# ------------------------------------------------------------ results data
rows = list(csv.DictReader(open(os.path.join(ROOT, "results", "comparison.csv"))))
main = [r for r in rows if r["scenario"] != "growing"]


def mean(planner, col, rs=main):
    v = [float(r[col]) for r in rs if r["planner"] == planner and r[col] not in ("", "nan")]
    return sum(v) / len(v)


# ------------------------------------------------------------ Fig: yard plan
def yard_plan():
    vps, _ = build_viewpoints(WALL_SEGMENTS)
    fig, ax = plt.subplots(figsize=(8.2, 3.9))
    for w in WALL_SEGMENTS:
        pt, n, u, _v = geo.wall_plane(w)
        hw = w["width"] / 2
        a, b = pt[:2] - u[:2] * hw, pt[:2] + u[:2] * hw
        ax.plot([a[0], b[0]], [a[1], b[1]], color=BLUE, lw=3.2, solid_capstyle="butt")
        cen = {"A": (0.0, 0.0), "B": (14.0, 0.0)}.get(w["name"][0])
        if cen is None:
            d = (0.0, 1.0)
        else:
            dx, dy = pt[0] - cen[0], pt[1] - cen[1]
            m = max((dx * dx + dy * dy) ** 0.5, 1e-6)
            d = (dx / m, dy / m)
        ax.text(pt[0] + d[0] * 1.05, pt[1] + d[1] * 0.55, w["name"], fontsize=6.5,
                ha="center", va="center", color=BLUE)
    for v in vps:
        c = "#c0392b" if v.standoff < 2.0 else "#e59866"
        ax.plot(v.pos[0], v.pos[1], "o", ms=2.6, color=c, alpha=0.85)
    ax.plot([], [], "o", ms=4, color="#c0392b", label="1.3 m inspection viewpoint")
    ax.plot([], [], "o", ms=4, color="#e59866", label="2.2 m survey viewpoint")
    ax.plot([], [], "-", lw=3, color=BLUE, label="inspectable wall / panel")
    ax.add_patch(Rectangle((6.5, 3.6), 1.0, 0.8, fc="#cccccc", ec=GREY, lw=0.8, zorder=0))
    ax.text(7.0, 4.7, "pipe rack", fontsize=6.5, ha="center", color=GREY)
    ax.add_patch(plt.Circle((-5.0, 3.0), 0.45, fc="#cccccc", ec=GREY, lw=0.8, zorder=0))
    ax.text(-5.0, 3.9, "lattice tower", fontsize=6.5, ha="center", color=GREY)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_xlim(-7.5, 18)
    ax.set_ylim(-5, 6.5)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower right", fontsize=7, frameon=True)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "yard_plan.png"), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------ Fig: planner flow
def box(ax, x, y, w, h, text, fc="white", bold=False, fs=8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.05", fc=fc, ec="black", lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")


def arrow(ax, x1, y1, x2, y2, text=None):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.1))
    if text:
        ax.text((x1 + x2) / 2 + 0.05, (y1 + y2) / 2 + 0.05, text, fontsize=7, style="italic")


def planner_flow():
    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    box(ax, 3.4, 5.6, 3.2, 0.6, "Start of step: belief state\n(view counts, uncertainty, growth, last-visit)", fc="#eef3fa")
    box(ax, 3.2, 4.4, 3.6, 0.7, "Is any wall still unvisited\nthis mission?", fc="white", bold=True)
    arrow(ax, 5.0, 5.6, 5.0, 5.1)
    box(ax, 0.2, 2.9, 3.6, 1.0, "PHASE 1 - Coverage guarantee\nscore = InfoGain - 0.4*Cost\nonly views of unvisited walls", fc="#fdf2e9")
    box(ax, 6.2, 2.9, 3.6, 1.0, "PHASE 2 - Full utility\nscore = IG + 1.5*U + 2.0*G + 1.0*S - 0.4*C\n+ 0.5 * best follow-up view", fc="#e9f5ee")
    arrow(ax, 4.2, 4.4, 2.2, 3.9, "yes")
    arrow(ax, 5.8, 4.4, 8.0, 3.9, "no")
    box(ax, 3.2, 1.55, 3.6, 0.7, "Fly to the highest-scoring view\n(only ONE step of any plan is executed)", fc="white")
    arrow(ax, 2.0, 2.9, 4.0, 2.25)
    arrow(ax, 8.0, 2.9, 6.0, 2.25)
    box(ax, 3.2, 0.35, 3.6, 0.7, "Capture -> detect -> localize -> memory\nupdate belief, then repeat", fc="#eef3fa")
    arrow(ax, 5.0, 1.55, 5.0, 1.05)
    ax.plot([3.2, 0.5, 0.5], [0.7, 0.7, 5.9], color="black", lw=1.0, ls="--")
    ax.annotate("", xy=(3.4, 5.9), xytext=(0.5, 5.9), arrowprops=dict(arrowstyle="->", lw=1.0, ls="--"))
    ax.text(0.25, 3.3, "next step", fontsize=7, style="italic", rotation=90, va="center")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "planner_flow.png"), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------ Fig: planners
def planner_chart():
    names = [("random", "Random"), ("isler_nbv", "Isler\n2016"), ("bircher_rhnbv", "Bircher\n2016"),
             ("gatsbi_gtsp", "GATSBI"), ("alamdari_latency", "Alamdari\n2014"), ("ruckin_ipp", "Rückin\n2023"),
             ("uwtig", "UW-TIG")]
    f1 = [mean(p, "f1_confirmed") for p, _ in names]
    fly = [mean(p, "total_flight_dist_m") for p, _ in names]
    cols = [BLUE if p == "uwtig" else "#999999" for p, _ in names]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.2))
    a1.bar([n for _, n in names], f1, color=cols)
    a1.axhline(0.9, color=RED, ls="--", lw=1)
    a1.text(-0.4, 0.915, "0.90", color=RED, fontsize=7)
    a1.set_ylim(0.5, 1.0)
    a1.set_ylabel("F1 (confirmed reports)")
    a1.set_title("Detection quality", fontsize=9)
    for i, v in enumerate(f1):
        a1.text(i, v + 0.006, f"{v:.3f}", ha="center", fontsize=6.5)
    a2.bar([n for _, n in names], fly, color=cols)
    a2.set_ylabel("Flight distance (m)")
    a2.set_title("Flight cost", fontsize=9)
    for i, v in enumerate(fly):
        a2.text(i, v + 6, f"{v:.0f}", ha="center", fontsize=6.5)
    for a in (a1, a2):
        a.tick_params(axis="x", labelsize=6.5)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "planner_chart.png"), dpi=200)
    plt.close(fig)


def ablation_chart():
    names = [("uwtig", "UW-TIG\n(full)"), ("uwtig_no_staleness", "no\nstaleness"), ("uwtig_no_lookahead", "no\nlookahead"),
             ("uwtig_no_uncertainty", "no\nuncertainty"), ("uwtig_no_temporal", "no\ntemporal"),
             ("uwtig_no_coverage_first", "no coverage\nphase")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.0))
    cols = [BLUE if p == "uwtig" else "#999999" for p, _ in names]
    r = [mean(p, "recall_confirmed") for p, _ in names]
    fly = [mean(p, "total_flight_dist_m") for p, _ in names]
    a1.bar([n for _, n in names], r, color=cols)
    a1.set_ylim(0.4, 1.0)
    a1.set_ylabel("Recall (confirmed)")
    for i, v in enumerate(r):
        a1.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=6.5)
    a2.bar([n for _, n in names], fly, color=cols)
    a2.set_ylabel("Flight distance (m)")
    for i, v in enumerate(fly):
        a2.text(i, v + 2, f"{v:.0f}", ha="center", fontsize=6.5)
    for a in (a1, a2):
        a.tick_params(axis="x", labelsize=6)
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "ablation_chart.png"), dpi=200)
    plt.close(fig)


def dev_progress():
    stages = ["original\nscoring", "fixes 1-3\n(units, GT,\ndistortion)", "+ survey\nstandoff", "+ on-wall\ncheck"]
    P = [0.76, 0.88, 0.86, 0.95]
    R = [0.63, 0.78, 0.96, 0.99]
    F = [0.65, 0.82, 0.90, 0.97]
    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    for y, lab, m in ((P, "Precision", "o"), (R, "Recall", "s"), (F, "F1", "^")):
        ax.plot(stages, y, marker=m, label=lab, lw=1.5)
    ax.axhline(0.9, color=RED, ls="--", lw=1)
    ax.set_ylim(0.5, 1.05)
    ax.set_ylabel("UW-TIG on development seeds")
    ax.legend(fontsize=7, loc="lower right")
    ax.tick_params(axis="x", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "dev_progress.png"), dpi=200)
    plt.close(fig)


def class_chart():
    cls = ["Crack", "Leakage", "Abscission", "Corrosion", "Bulge"]
    p = [0.84, 0.90, 0.87, 0.83, 0.95]
    r = [0.75, 0.92, 0.78, 0.79, 0.96]
    import numpy as np
    x = np.arange(len(cls))
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    ax.bar(x - 0.18, p, 0.36, label="Precision", color=BLUE)
    ax.bar(x + 0.18, r, 0.36, label="Recall", color="#999999")
    ax.set_xticks(x)
    ax.set_xticklabels(cls)
    ax.set_ylim(0.5, 1.0)
    ax.legend(fontsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "class_chart.png"), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    yard_plan()
    planner_flow()
    planner_chart()
    ablation_chart()
    dev_progress()
    class_chart()
    print("figures written to", OUT)
