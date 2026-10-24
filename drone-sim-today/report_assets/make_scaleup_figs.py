# -*- coding: utf-8 -*-
"""Figures for the scale-up experiments (31-wall yard, multi-dataset detector).
Reads results/scaleup_summary.json and results/detector_extra.json; run from
drone-sim-today/ after experiments/analyze_scaleup.py."""
import json
import os
import sys

os.environ["UWTIG_YARD"] = "large"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = os.path.join(HERE, "dissertation_figs")
import geometry as geo  # noqa: E402
from planning.viewpoints import build_viewpoints  # noqa: E402
from sim_house import WALL_SEGMENTS  # noqa: E402

plt.rcParams.update({"font.family": "serif", "font.size": 10})
BLUE, GREY, RED, ORANGE = "#1f3a5f", "#777777", "#a61c1c", "#e59866"
SC = json.load(open(os.path.join(ROOT, "results", "scaleup_summary.json")))
DET = json.load(open(os.path.join(ROOT, "results", "detector_extra.json")))

LABEL = {"uwtig": "UW-TIG", "ruckin_ipp": "Rückin IPP", "gatsbi_gtsp": "GATSBI", "alamdari_latency": "Alamdari",
         "bircher_rhnbv": "Bircher", "isler_nbv": "Isler-NBV", "random": "Random"}


def yard_large():
    vps, _ = build_viewpoints(WALL_SEGMENTS)
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    for w in WALL_SEGMENTS:
        pt, n, u, _v = geo.wall_plane(w)
        hw = w["width"] / 2
        a, b = pt[:2] - u[:2] * hw, pt[:2] + u[:2] * hw
        ax.plot([a[0], b[0]], [a[1], b[1]], color=BLUE, lw=3.0, solid_capstyle="butt")
    for v in vps:
        ax.plot(v.pos[0], v.pos[1], "o", ms=1.8, color="#c0392b" if v.standoff < 2.0 else ORANGE, alpha=0.8)
    for name, (x, y) in {"A": (0, 0), "B": (14, 0.6), "C": (-12, 0), "D": (0, 12), "E": (14, 11), "F": (-12, 12)}.items():
        ax.text(x, y, name, fontsize=11, ha="center", va="center", color=BLUE, weight="bold")
    ax.add_patch(Rectangle((6.5, 3.6), 1.0, 0.8, fc="#cccccc", ec=GREY, lw=0.8, zorder=0))
    ax.add_patch(plt.Circle((-5.0, 3.0), 0.45, fc="#cccccc", ec=GREY, lw=0.8, zorder=0))
    ax.plot([], [], "o", ms=4, color="#c0392b", label="1.3 m inspection viewpoint")
    ax.plot([], [], "o", ms=4, color=ORANGE, label="2.2 m survey viewpoint")
    ax.plot([], [], "-", lw=3, color=BLUE, label="inspectable wall / panel")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_xlim(-17, 19)
    ax.set_ylim(-13, 16)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower right", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "yard_large.png"), dpi=200)
    plt.close(fig)


def f1_by_yard():
    order = [p for p in ["uwtig", "ruckin_ipp", "gatsbi_gtsp", "alamdari_latency", "bircher_rhnbv", "isler_nbv", "random"]
             if p in SC["small_old"]["planners"]]
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6))
    for ax, key, title in ((axes[0], "f1_confirmed", "F1 (confirmed)"), (axes[1], "total_flight_dist_m", "Flight distance (m)")):
        x = range(len(order))
        for off, name, col in ((-0.2, "small_old", GREY), (0.2, "large_old", BLUE)):
            vals = [SC[name]["planners"][p][key] for p in order]
            ax.bar([i + off for i in x], vals, 0.38, color=col, label={"small_old": "9 walls", "large_old": "31 walls"}[name])
        ax.set_xticks(list(x))
        ax.set_xticklabels([LABEL[p] for p in order], rotation=35, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(fontsize=8)
    axes[1].set_yscale("log")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "f1_by_yard.png"), dpi=200)
    plt.close(fig)


def detector_chart():
    sets = [("mbdd", "MBDD2025 test"), ("dacl", "dacl10k held-out")]
    fig, ax = plt.subplots(figsize=(5.4, 3.3))
    for k, (s, lab) in enumerate(sets):
        for off, m, col in ((-0.19, "old", GREY), (0.19, "new", BLUE)):
            v = DET[m][s]["map50"]
            ax.bar(k + off, v, 0.36, color=col, label=("original" if m == "old" else "fine-tuned") if k == 0 else None)
            ax.text(k + off, v + 0.015, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(sets)))
    ax.set_xticklabels([l for _, l in sets])
    ax.set_ylabel("mAP50")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "detector_chart.png"), dpi=200)
    plt.close(fig)


def paired_chart():
    d = SC["large_new"]["uwtig_vs"]
    order = [p for p in ["ruckin_ipp", "gatsbi_gtsp", "alamdari_latency", "bircher_rhnbv", "isler_nbv", "random"] if p in d]
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    for i, p in enumerate(order):
        m, (lo, hi) = d[p]["mean_diff"], d[p]["ci"]
        ax.errorbar(m, i, xerr=[[m - lo], [hi - m]], fmt="o", color=BLUE, capsize=3)
    ax.axvline(0, color=RED, lw=1)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([LABEL[p] for p in order])
    ax.set_xlabel("UW-TIG F1 minus planner F1 (mean over seeds, 95% bootstrap CI)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "paired_chart.png"), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    yard_large()
    f1_by_yard()
    detector_chart()
    paired_chart()
    print("scale-up figures written")
