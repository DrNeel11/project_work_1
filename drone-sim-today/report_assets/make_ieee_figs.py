# -*- coding: utf-8 -*-
"""IEEE-style figures for the review deck (and reusable in the paper / dissertation).

Conventions followed: Times-style serif text, black strokes on white with light
grey fills so the figures survive black-and-white printing, bold borders instead
of colour to mark this work's contributions, sub-figure labels (a)/(b), the
caption lives in the document (not inside the figure). Double-column width is
7.16 in, single-column 3.5 in. Every figure is saved as PNG (300 dpi) and as a
vector PDF.

Run from drone-sim-today/:  venv python report_assets/make_ieee_figs.py"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "deck_figs")
os.makedirs(OUT, exist_ok=True)
TS = json.load(open(os.path.join(ROOT, "results", "ten_seed_summary.json")))

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8,
    "axes.linewidth": 0.7,
    "pdf.fonttype": 42,
})
FSC = 1.0  # font scale for the wide slide version of the architecture
INK, GREY, LIGHT, MID = "#000000", "#555555", "#eeeeee", "#d9d9d9"


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300)
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    plt.close(fig)


# ---------------------------------------------------------------- architecture
def box(ax, x, y, w, h, title, body="", novel=False, fill=LIGHT, fs=7.2):
    fs = fs * FSC
    lw = 1.8 if novel else 0.8
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", fc=fill, ec=INK, lw=lw, zorder=3))
    if body:
        ax.text(x + w / 2, y + h - 1.0, title, ha="center", va="top", fontsize=fs, fontweight="bold", zorder=4)
        ax.text(x + w / 2, y + h - 3.4, body, ha="center", va="top", fontsize=fs - 0.8, linespacing=1.25, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs, fontweight="bold", zorder=4)


def frame(ax, x, y, w, h, label):
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=GREY, lw=0.7, ls=(0, (4, 2)), zorder=1))
    ax.text(x + 0.9, y + h - 0.9, label, ha="left", va="top", fontsize=7.4 * FSC, style="italic", color=INK, zorder=2)


def arrow(ax, pts, label=None, lpos=None, dashed=False, ha="center", rot=0):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1], ys[:-1], color=INK, lw=0.8, ls=(0, (3, 2)) if dashed else "-", zorder=2, solid_capstyle="butt")
    ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8, shrinkA=0, shrinkB=0,
                                                                 mutation_scale=7), zorder=5)
    if label:
        ax.text(*lpos, label, fontsize=6.4 * FSC, ha=ha, va="center", rotation=rot, style="italic", zorder=6,
                bbox=dict(fc="white", ec="none", pad=0.6))


def architecture(figsize=(7.16, 5.05), name="architecture"):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 70.5)
    ax.axis("off")

    # columns: x0, width
    c1, c2, c3, c4 = (1, 21), (26.5, 21), (52, 22.5), (79.5, 19.5)
    top, bot = 7.6, 62.2
    frame(ax, c1[0], top, c1[1], bot - top, "Environment (PyBullet)")
    frame(ax, c2[0], top, c2[1], bot - top, "Perception")
    frame(ax, c3[0], top, c3[1], bot - top, "Localization and memory")
    frame(ax, c4[0], top, c4[1], bot - top, "Planning")

    H = 11.2
    L1, L2, L3 = 46.2, 28.4, 10.6  # bottom y of the three levels

    # Environment
    box(ax, c1[0] + 1.5, L1, c1[1] - 3, H, "Camera", "320×240 frame\n60° field of view")
    box(ax, c1[0] + 1.5, L2, c1[1] - 3, H, "Yard scene", "9 / 31 walls, MBDD2025\ntextures, 4 scenarios,\nground-truth defects")
    box(ax, c1[0] + 1.5, L3, c1[1] - 3, H, "Move to view", "kinematic (sweeps)\nPID flight (demo)")
    # Perception
    box(ax, c2[0] + 1.5, L1, c2[1] - 3, H, "Resample", "320×240 → 320×320\n(square pixels)")
    box(ax, c2[0] + 1.5, L2, c2[1] - 3, H, "YOLOv8s × 5", "original + 4 photometric\nvariants (TTA);\nconfidence ≥ 0.25")
    box(ax, c2[0] + 1.5, L3, c2[1] - 3, H, "Detections", "box, class, confidence,\nuncertainty = std of\nconfidence over 5 passes", novel=True)
    # Localization and memory
    box(ax, c3[0] + 1.5, L1, c3[1] - 3, H, "Report rule", "defect (wall, class) after\n≥ 3 looks or confidence\n≥ 0.45")
    box(ax, c3[0] + 1.5, L2 - 3.6, c3[1] - 3, H + 6.4, "Defect memory",
        "PostgreSQL + pgvector:\ndetection log, 32-D embedding,\nnearest-neighbour match,\n0.35 m spatial gate\nNeo4j: Defect–Mission–Wall\ngraph, growth chain", novel=True)
    box(ax, c3[0] + 1.5, L3, c3[1] - 3, H, "Ray-cast", "pixel ray ∩ wall plane\n→ 3-D position, size (m)")
    # Planning
    box(ax, c4[0] + 1.5, L1, c4[1] - 3, H, "Viewpoint graph", "54 / 186 views\n1.3 m and 2.2 m standoff")
    box(ax, c4[0] + 1.5, L2, c4[1] - 3, H, "Mission belief", "per wall cell: views,\nuncertainty, growth,\nlast visit", novel=True)
    box(ax, c4[0] + 1.5, L3, c4[1] - 3, H, "UW-TIG", "1) coverage phase\n2) utility + 2-step\nlookahead", novel=True)

    mid = H / 2
    # camera -> resample
    arrow(ax, [(c1[0] + c1[1] - 1.5, L1 + mid), (c2[0] + 1.5, L1 + mid)])
    # resample -> yolo -> detections
    arrow(ax, [(c2[0] + c2[1] / 2, L1), (c2[0] + c2[1] / 2, L2 + H)])
    arrow(ax, [(c2[0] + c2[1] / 2, L2), (c2[0] + c2[1] / 2, L3 + H)])
    # detections -> ray-cast
    arrow(ax, [(c2[0] + c2[1] - 1.5, L3 + mid), (c3[0] + 1.5, L3 + mid)])
    # ray-cast -> memory
    arrow(ax, [(c3[0] + c3[1] / 2, L3 + H), (c3[0] + c3[1] / 2, L2 - 3.6)])
    # memory -> report
    arrow(ax, [(c3[0] + c3[1] / 2, L2 + H + 2.8), (c3[0] + c3[1] / 2, L1)])
    # memory -> belief (priors from earlier missions)
    arrow(ax, [(c3[0] + c3[1] - 1.5, L2 + mid), (c4[0] + 1.5, L2 + mid)], "priors", (c3[0] + c3[1] + 1.55, L2 + mid + 2.2))
    # belief -> UW-TIG
    arrow(ax, [(c4[0] + c4[1] / 2, L2), (c4[0] + c4[1] / 2, L3 + H)])
    # viewpoint graph -> UW-TIG (right margin lane)
    xr = c4[0] + c4[1] - 0.8
    arrow(ax, [(c4[0] + c4[1] - 1.5, L1 + mid), (xr + 0.0, L1 + mid), (xr + 0.0, L3 + mid), (c4[0] + c4[1] - 1.5, L3 + mid)])
    # detection uncertainty -> belief is carried through memory; next view lane along the bottom
    yb = 3.4
    arrow(ax, [(c4[0] + c4[1] / 2, L3), (c4[0] + c4[1] / 2, yb), (c1[0] + c1[1] / 2, yb), (c1[0] + c1[1] / 2, L3)],
          "next viewpoint (only the first step of the plan is flown)", (50, yb), ha="center")
    # move -> scene -> camera (upwards)
    arrow(ax, [(c1[0] + c1[1] / 2, L3 + H), (c1[0] + c1[1] / 2, L2)])
    arrow(ax, [(c1[0] + c1[1] / 2, L2 + H), (c1[0] + c1[1] / 2, L1)])

    # evaluation bar
    ax.add_patch(FancyBboxPatch((c3[0], 64.2), c4[0] + c4[1] - c3[0], 5.2, boxstyle="round,pad=0,rounding_size=0.8", fc="white", ec=INK, lw=0.8))
    ax.text((c3[0] + c4[0] + c4[1]) / 2, 66.8, "Evaluation: confirmed precision / recall / F1, flight distance, coverage\nten seeds, bootstrap 95% confidence intervals",
            ha="center", va="center", fontsize=6.6 * FSC, fontweight="bold", linespacing=1.3)
    arrow(ax, [(c3[0] + c3[1] / 2, L1 + H), (c3[0] + c3[1] / 2, 64.2)])

    # legend
    ax.add_patch(FancyBboxPatch((1, 65.0), 3.6, 3.4, boxstyle="round,pad=0,rounding_size=0.5", fc=LIGHT, ec=INK, lw=1.8))
    ax.text(5.6, 66.7, "contribution of this work", fontsize=6.8 * FSC, va="center")
    ax.add_patch(FancyBboxPatch((26.5, 65.0), 3.6, 3.4, boxstyle="round,pad=0,rounding_size=0.5", fc=LIGHT, ec=INK, lw=0.8))
    ax.text(31.1, 66.7, "standard component", fontsize=6.8 * FSC, va="center")
    fig = ax.figure
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    save(fig, name)


# ---------------------------------------------------------------- decision flow
def decision_flow():
    fig, ax = plt.subplots(figsize=(7.16, 3.5))
    ax.set_xlim(0, 100)
    ax.set_ylim(-3, 46)
    ax.axis("off")

    def b(x, y, w, h, t, bold=False, fill="white", lw=0.8, fs=7.2):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", fc=fill, ec=INK, lw=lw, zorder=3))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.3, zorder=4)

    def dia(cx, cy, w, h, t):
        ax.add_patch(plt.Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)], fc="white", ec=INK, lw=0.8, zorder=3))
        ax.text(cx, cy, t, ha="center", va="center", fontsize=7, linespacing=1.25, zorder=4)

    b(1, 17, 15, 12, "Belief state:\nviews, uncertainty,\ngrowth, last visit", fill=LIGHT)
    dia(30, 23, 17, 15, "Any wall\nunseen this\nmission?")
    b(46, 33, 24, 11, "Phase 1: coverage\nscore = InfoGain − 0.4 Cost\nunseen walls only", fill=MID, lw=1.8)
    b(46, 2, 24, 13, "Phase 2: full utility\nIG + 1.5 U + 2.0 G + 1.0 S\n− 0.4 C + 0.5 (best next view)", fill=MID, lw=1.8)
    b(77, 17, 22, 12, "Fly to the best view;\nexecute one step\nof the plan", fill="white")
    b(77, 1.5, 22, 9.5, "Capture, detect,\nlocalize, update memory", fill=LIGHT)

    def arr(pts, label=None, lp=None):
        xs, ys = zip(*pts)
        ax.plot(xs[:-1], ys[:-1], color=INK, lw=0.8, zorder=2)
        ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8, shrinkA=0, shrinkB=0, mutation_scale=7), zorder=5)
        if label:
            ax.text(*lp, label, fontsize=6.8, style="italic", ha="center", va="center", bbox=dict(fc="white", ec="none", pad=0.5), zorder=6)

    arr([(16, 23), (21.5, 23)])
    arr([(30, 30.5), (30, 38.5), (46, 38.5)], "yes", (33, 36))
    arr([(30, 15.5), (30, 8.5), (46, 8.5)], "no", (33, 11))
    arr([(70, 38.5), (88, 38.5), (88, 29)])
    arr([(70, 8.5), (88, 8.5)] if False else [(70, 8.5), (74, 8.5), (74, 23), (77, 23)])
    arr([(88, 17), (88, 11)])
    arr([(88, 1.5), (88, -1.5), (8.5, -1.5), (8.5, 17)], "next step", (48, -1.5))
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.005)
    save(fig, "decision_flow")


# ---------------------------------------------------------------- charts
MARK = {"uwtig": ("o", "#000000"), "alamdari_latency": ("s", "#555555"), "gatsbi_gtsp": ("^", "#555555"),
        "ruckin_ipp": ("D", "#555555"), "random": ("v", "#888888"), "bircher_rhnbv": ("P", "#888888"), "isler_nbv": ("X", "#888888")}
NAMES = {"uwtig": "UW-TIG", "alamdari_latency": "Alamdari", "gatsbi_gtsp": "GATSBI", "ruckin_ipp": "Rückin",
         "random": "Random", "bircher_rhnbv": "Bircher", "isler_nbv": "Isler"}
OFF = {"small": {"uwtig": (-46, 5), "gatsbi_gtsp": (6, -12), "alamdari_latency": (-6, 9), "ruckin_ipp": (6, -11)},
       "large": {"uwtig": (-52, 16), "gatsbi_gtsp": (-56, -20), "alamdari_latency": (3, 9), "ruckin_ipp": (6, 5)}}


def tradeoff():
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 3.15))
    for ax, yard, lab in zip(axes, ("small", "large"), ("(a) 9-wall yard", "(b) 31-wall yard")):
        for k, name in NAMES.items():
            d = TS[yard][k]
            m, c = MARK[k]
            ci = d["ci"]
            ax.errorbar(d["flight"], d["f1"], yerr=[[d["f1"] - ci[0]], [ci[1] - d["f1"]]], fmt=m, color=c, mfc="black" if k == "uwtig" else "white",
                        mec=c, ms=6.5 if k == "uwtig" else 5, capsize=2, lw=0.8, zorder=3)
            dx, dy = OFF[yard].get(k, (6, 3))
            ax.annotate(name, (d["flight"], d["f1"]), xytext=(dx, dy), textcoords="offset points", fontsize=7.2,
                        fontweight="bold" if k == "uwtig" else "normal",
                        arrowprops=dict(arrowstyle="-", color=GREY, lw=0.5) if (yard == "large" and k in ("uwtig", "gatsbi_gtsp")) else None)
        ax.set_xscale("log")
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xticks([30, 60, 100, 200, 400] if yard == "small" else [100, 300, 1000, 3000])
        ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_ylim(0.4, 1.0)
        ax.set_xlim(*((24, 560) if yard == "small" else (110, 4200)))
        ax.set_xlabel("Flight distance over three missions (m)")
        ax.grid(alpha=0.3, lw=0.4)
        ax.text(0.5, -0.28, lab, transform=ax.transAxes, ha="center", fontsize=8)
    axes[0].set_ylabel("F1 (confirmed)")
    fig.subplots_adjust(left=0.07, right=0.99, top=0.97, bottom=0.235, wspace=0.18)
    save(fig, "tradeoff")


def ablation():
    keys = [("uwtig", "UW-TIG"), ("uwtig_no_coverage_first", "no\ncoverage"), ("uwtig_no_uncertainty", "no\nuncert."),
            ("uwtig_no_temporal", "no\ngrowth"), ("uwtig_no_staleness", "no\nstaleness"), ("uwtig_no_lookahead", "no\nlookahead")]
    fig, axes = plt.subplots(1, 2, figsize=(7.16, 2.85))
    for ax, yard, lab in zip(axes, ("small", "large"), ("(a) 9-wall yard", "(b) 31-wall yard")):
        vals = [TS[yard][k]["f1"] for k, _ in keys]
        fills = ["black", "#bdbdbd", "white", "white", "white", "white"]
        hatch = [None, None, "////", "\\\\\\\\", "xxxx", "....."]
        for i, (v, f, h) in enumerate(zip(vals, fills, hatch)):
            ax.bar(i, v, width=0.62, fc=f, ec="black", lw=0.7, hatch=h)
            ax.text(i, v + 0.012, f"{v:.3f}", ha="center", fontsize=7)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels([n for _, n in keys], fontsize=7.2)
        ax.set_ylim(0.4, 1.05)
        ax.grid(axis="y", alpha=0.3, lw=0.4)
        ax.set_axisbelow(True)
        ax.text(0.5, -0.3, lab, transform=ax.transAxes, ha="center", fontsize=8)
    axes[0].set_ylabel("F1 (confirmed)")
    fig.subplots_adjust(left=0.07, right=0.99, top=0.97, bottom=0.27, wspace=0.18)
    save(fig, "ablation")


if __name__ == "__main__":
    architecture()
    FSC = 1.0
    globals()["FSC"] = 1.3
    architecture(figsize=(9.6, 5.0), name="architecture_slide")
    globals()["FSC"] = 1.0
    decision_flow()
    tradeoff()
    ablation()
    print("wrote", OUT)
