# -*- coding: utf-8 -*-
"""Charts for the review deck, drawn from results/ten_seed_summary.json so the
slides and the paper quote the same ten-seed numbers.
Run from drone-sim-today/:  venv python report_assets/make_deck_figs.py"""
import json
import os

import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "deck_figs")
os.makedirs(OUT, exist_ok=True)
TS = json.load(open(os.path.join(ROOT, "results", "ten_seed_summary.json")))

NAVY, RED, GREY = "#1f3a5f", "#a51c30", "#8a8f98"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 11, "axes.linewidth": 0.8,
                     "axes.spines.top": False, "axes.spines.right": False})
NAMES = {"uwtig": "UW-TIG", "alamdari_latency": "Alamdari", "gatsbi_gtsp": "GATSBI", "ruckin_ipp": "Rückin",
         "random": "Random", "bircher_rhnbv": "Bircher", "isler_nbv": "Isler"}


def tradeoff():
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    for ax, yard, title in zip(axes, ("small", "large"), ("9-wall yard", "31-wall yard")):
        for k, name in NAMES.items():
            d = TS[yard][k]
            ci = d.get("ci")
            c = RED if k == "uwtig" else NAVY
            if ci:
                ax.errorbar(d["flight"], d["f1"], yerr=[[d["f1"] - ci[0]], [ci[1] - d["f1"]]], fmt="o", color=c,
                            ms=8 if k == "uwtig" else 6, capsize=3, lw=1.2, zorder=3)
            else:
                ax.plot(d["flight"], d["f1"], "o", color=c, ms=6)
            if yard == "small":
                off = {"uwtig": (-52, 4), "gatsbi_gtsp": (6, -16), "alamdari_latency": (-8, 12), "ruckin_ipp": (6, -14)}
            else:
                off = {"uwtig": (-62, 22), "gatsbi_gtsp": (-66, -26), "alamdari_latency": (4, 10), "ruckin_ipp": (6, 6)}
            dx, dy = off.get(k, (6, 4))
            ax.annotate(name, (d["flight"], d["f1"]), xytext=(dx, dy), textcoords="offset points", fontsize=9.5,
                        color=c, fontweight="bold" if k == "uwtig" else "normal",
                        arrowprops=dict(arrowstyle="-", color=c, lw=0.6) if k in ("uwtig", "gatsbi_gtsp") and yard == "large" else None)
        ax.set_xscale("log")
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xticks([30, 100, 300, 1000, 3000] if yard == "large" else [30, 60, 100, 200, 400])
        ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_ylim(0.4, 1.0)
        ax.set_xlabel("Flight distance over three missions (m, log scale)")
        ax.set_title(title, loc="left", fontsize=12, color=NAVY, fontweight="bold")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("F1 (confirmed), ten seeds")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "tradeoff.png"), dpi=200)
    plt.close(fig)


def ablation():
    keys = [("uwtig", "UW-TIG"), ("uwtig_no_coverage_first", "no coverage\nphase"), ("uwtig_no_uncertainty", "no\nuncertainty"),
            ("uwtig_no_temporal", "no\ngrowth"), ("uwtig_no_staleness", "no\nstaleness"), ("uwtig_no_lookahead", "no\nlookahead")]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6))
    for ax, yard, title in zip(axes, ("small", "large"), ("9-wall yard", "31-wall yard")):
        vals = [TS[yard][k]["f1"] for k, _ in keys]
        cols = [RED if k == "uwtig" else (NAVY if k == "uwtig_no_coverage_first" else GREY) for k, _ in keys]
        b = ax.bar(range(len(keys)), vals, color=cols, width=0.65)
        for r, v in zip(b, vals):
            ax.text(r.get_x() + r.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
        ax.set_xticks(range(len(keys)))
        ax.set_xticklabels([n for _, n in keys], fontsize=9)
        ax.set_ylim(0.4, 1.05)
        ax.set_title(title, loc="left", fontsize=12, color=NAVY, fontweight="bold")
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("F1 (confirmed), ten seeds")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "ablation.png"), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    tradeoff()
    ablation()
    print("wrote", OUT)
