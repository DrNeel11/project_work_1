# Black-and-white system architecture diagram for Fig. 4.1 (the word-processor copy of the report)
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig41_architecture.png")
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"], "font.size": 7.5})
W, H = 4.95, 2.35
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, 100)
ax.set_ylim(0, 47.5)
ax.axis("off")

bw, bh = 21.0, 13.0
xs = [1.5, 26.5, 51.5, 76.5]
y_top, y_bot = 29.0, 5.0


def box(x, y, title, sub, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.25,rounding_size=1.2", fc="white", ec="black", lw=1.1 if bold else 0.8))
    ax.text(x + bw / 2, y + bh - 3.6, title, ha="center", va="center", fontsize=7.4, weight="bold")
    ax.text(x + bw / 2, y + 4.3, sub, ha="center", va="center", fontsize=6.2, linespacing=1.15)


def arrow(p, q, style="-|>", ls="-", lw=0.9):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle=style, lw=lw, color="black", linestyle=ls, shrinkA=0, shrinkB=0, mutation_scale=8))


box(xs[0], y_top, "Scenario", "environment,\ndefect textures")
box(xs[1], y_top, "Planner", "picks the next\nviewpoint (UW-TIG)", bold=True)
box(xs[2], y_top, "Capture", "rendered frame\n(kinematic or PID)")
box(xs[3], y_top, "Detector", "YOLOv8s + TTA\nuncertainty")
box(xs[3], y_bot, "Localisation", "ray cast onto the\nwall plane (3-D)")
box(xs[2], y_bot, "Memory", "PostgreSQL + pgvector,\nNeo4j defect graph")
box(xs[1], y_bot, "Mission belief", "coverage, uncertainty,\ngrowth, staleness")

ym_top, ym_bot = y_top + bh / 2, y_bot + bh / 2
arrow((xs[0] + bw + 0.4, ym_top), (xs[1] - 0.4, ym_top))
arrow((xs[1] + bw + 0.4, ym_top), (xs[2] - 0.4, ym_top))
arrow((xs[2] + bw + 0.4, ym_top), (xs[3] - 0.4, ym_top))
arrow((xs[3] + bw / 2, y_top - 0.4), (xs[3] + bw / 2, y_bot + bh + 0.4))
arrow((xs[3] - 0.4, ym_bot), (xs[2] + bw + 0.4, ym_bot))
arrow((xs[2] - 0.4, ym_bot), (xs[1] + bw + 0.4, ym_bot))
# feedback: belief -> planner (thick)
arrow((xs[1] + bw / 2, y_bot + bh + 0.4), (xs[1] + bw / 2, y_top - 0.4), lw=1.8)
ax.text(xs[1] + bw / 2 + 1.6, (y_top + y_bot + bh) / 2, "feedback", fontsize=6.2, style="italic", ha="left", va="center")
# report output
arrow((xs[2] + bw / 2, y_bot - 0.4), (xs[2] + bw / 2, 1.2), ls="--")
ax.text(xs[2] + bw / 2, 0.0, "reported (wall, class) pairs", fontsize=6.0, ha="center", va="top", style="italic")
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.07)
fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT)
