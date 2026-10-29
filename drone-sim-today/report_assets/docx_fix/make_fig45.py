# Black-and-white decision-flow diagram for Fig. 4.5 (one planning step of UW-TIG)
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig45_decision_flow.png")
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"], "font.size": 7})
W, H = 4.77, 2.71
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, 100)
ax.set_ylim(0, 57)
ax.axis("off")


def rbox(x0, y0, x1, y1, title, sub=None, lw=0.9):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0.2,rounding_size=1.2", fc="white", ec="black", lw=lw))
    cx = (x0 + x1) / 2
    if sub:
        ax.text(cx, y1 - 3.2, title, ha="center", va="center", fontsize=7.2, weight="bold")
        ax.text(cx, (y0 + y1) / 2 - 2.2, sub, ha="center", va="center", fontsize=6.2, linespacing=1.2)
    else:
        ax.text(cx, (y0 + y1) / 2, title, ha="center", va="center", fontsize=6.8, linespacing=1.2)


def line(pts, arrow=True, ls="-", lw=0.9):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] if arrow else xs, ys[:-1] if arrow else ys, color="black", lw=lw, ls=ls, solid_capstyle="butt")
    if arrow:
        ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", lw=lw, color="black", shrinkA=0, shrinkB=0, mutation_scale=8, linestyle="-"))
    else:
        pass


# start box
rbox(24, 46, 76, 56, "Start of a planning step", "belief and memory: coverage, uncertainty, growth, staleness")
# decision diamond
cx, cy, dw, dh = 50, 38.5, 36, 12
ax.add_patch(Polygon([(cx - dw / 2, cy), (cx, cy + dh / 2), (cx + dw / 2, cy), (cx, cy - dh / 2)], closed=True, fc="white", ec="black", lw=0.9))
ax.text(cx, cy, "Any wall still unvisited\nin this mission?", ha="center", va="center", fontsize=6.4, linespacing=1.15)
line([(50, 46), (50, cy + dh / 2)])
# two branches
rbox(2, 14, 45, 29, "Coverage phase", "use only the viewpoints of\nunvisited walls; score\nIG − 0.4·Cost")
rbox(54, 12, 97, 29, "Full-utility phase", "score every viewpoint\nU = 1.0·IG + 1.5·Unc + 2.0·Growth\n+ 1.0·Stale − 0.4·Cost, plus 0.5 ×\nthe best follow-up view")
line([(cx - dw / 2, cy), (23.5, cy), (23.5, 29)])
line([(cx + dw / 2, cy), (75.5, cy), (75.5, 29)])
ax.text(27, cy + 1.6, "yes", fontsize=6.2, style="italic", ha="center")
ax.text(73.5, cy + 1.6, "no", fontsize=6.2, style="italic", ha="center")
# pick box
rbox(26, 0.5, 74, 8.5, "Fly to the best-scoring viewpoint," + chr(10) + "capture, detect and update memory", lw=1.1)
line([(23.5, 14), (23.5, 11.2), (40, 11.2), (40, 8.5)])
line([(75.5, 12), (75.5, 11.2), (60, 11.2), (60, 8.5)])
# loop back to start
line([(74.2, 4.5), (99, 4.5), (99, 51), (76.4, 51)])
ax.text(98.2, 33, "next step", rotation=90, fontsize=6.2, style="italic", ha="right", va="center")
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT)
