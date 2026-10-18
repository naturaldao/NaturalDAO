"""Draw every figure from experiments/results/*.json in one consistent style.

Simulation estimates are drawn as points or bars with Wilson 95% intervals;
the exact values from ``pol2_agent_ballot.theory`` are drawn as thin dashed
lines or ticks, so agreement between the two is visible at a glance.

Run:  python experiments/make_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pol2_agent_ballot.theory import cascade, condorcet, consensus  # noqa: E402

HERE = Path(__file__).resolve().parent
RES, FIG = HERE / "results", HERE / "figures"

SEALED, OPEN, GREEN = "#2459C9", "#C46A12", "#1F8A5B"
INK, INK2, MUTED, GRID = "#121826", "#465166", "#6E7890", "#E3E7EE"
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "legend.frameon": False,
        "savefig.dpi": 180,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.15,
    }
)


def _note(fig, text):
    fig.text(0.01, -0.02, text, fontsize=8, color=MUTED, ha="left", va="top", wrap=True)


def fig_headline(h):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), gridspec_kw={"width_ratios": [1.15, 1]})
    names = ["Sealed", "Open sequential"]
    cols = [SEALED, OPEN]
    ax = axes[0]
    for i, r in enumerate(h):
        lo, hi = r["ci95"]
        ax.bar(i, r["accuracy"], width=0.56, color=cols[i])
        ax.errorbar(i, r["accuracy"], yerr=[[r["accuracy"] - lo], [hi - r["accuracy"]]], color=INK, capsize=4, lw=1)
        ex = r.get("exact_accuracy", condorcet(r["n"], r["p"]) if i == 0 else cascade(r["n"], r["p"], r["lead"])["accuracy"])
        ax.plot([i - 0.34, i + 0.34], [ex, ex], color=INK, lw=1.2, ls=(0, (3, 2)))
        ax.text(i, r["accuracy"] + 0.035, f"{r['accuracy']:.3f}", ha="center", color=INK, fontsize=10.5, fontweight="bold")
    ax.set_xticks([0, 1], names)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("P(collective decision correct)")
    ax.set_title(f"Accuracy of the collective decision\nN={h[0]['n']}, p={h[0]['p']}, {h[0]['trials']:,} runs each")
    ax.plot([], [], color=INK, lw=1.2, ls=(0, (3, 2)), label="exact (theory.py)")
    ax.legend(loc="upper right", fontsize=8.5)

    ax = axes[1]
    for i, r in enumerate(h):
        ax.bar(i, r["conformity_rate"], width=0.56, color=cols[i])
        ax.text(i, r["conformity_rate"] + 0.008, f"{r['conformity_rate']:.1%}", ha="center", color=INK, fontsize=10.5, fontweight="bold")
    ax.set_xticks([0, 1], names)
    ax.set_ylim(0, 0.3)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.set_title("Agents voting against their own evidence\nshare of all ballots")
    _note(fig, "Every run went through the full protocol (key ceremony, sealed envelopes, decryption, audit). Error bars: Wilson 95% intervals. "
          "Scripted agents; the figure shows the mechanism the protocol guards against, not the behaviour of language-model agents.")
    fig.tight_layout()
    fig.savefig(FIG / "headline.png")
    plt.close(fig)


def fig_sweep(sw):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    for ax, rows, key, xlabel in ((axes[0], sw["by_n"], "n", "number of agents N"), (axes[1], sw["by_p"], "p", "accuracy of each agent's evidence p")):
        for cond, col, label in (("sealed", SEALED, "Sealed"), ("open", OPEN, "Open sequential")):
            rs = sorted([r for r in rows if r["condition"] == cond], key=lambda r: r[key])
            xs = [r[key] for r in rs]
            ys = [r["accuracy"] for r in rs]
            err = [[y - r["ci95"][0] for y, r in zip(ys, rs)], [r["ci95"][1] - y for y, r in zip(ys, rs)]]
            ex = [r["exact_accuracy"] for r in rs]
            ax.plot(xs, ex, color=col, lw=1.2, ls=(0, (3, 2)))
            ax.errorbar(xs, ys, yerr=err, fmt="o", ms=5, color=col, mec="white", mew=1.2, elinewidth=1, capsize=0, label=label)
        if key == "p":
            ax.plot(xs, xs, color=MUTED, lw=0.9, ls=":")
            ax.text(xs[-1], xs[-1] - 0.03, "one agent", color=MUTED, fontsize=8, ha="right")
            ax.set_xticks(xs)
            ax.set_title(f"Accuracy vs evidence quality\nN={rows[0]['n']}")
        else:
            ax.set_xticks(xs)
            ax.set_title(f"Accuracy vs group size\np={rows[0]['p']}")
        ax.set_xlabel(xlabel)
        ax.set_ylim(0.5 if key == "p" else 0.7, 1.01)
        ax.set_ylabel("P(correct)")
    axes[0].legend(loc="lower right", fontsize=8.5)
    axes[0].plot([], [], color=INK2, lw=1.2, ls=(0, (3, 2)), label="exact")
    axes[0].legend(loc="lower right", fontsize=8.5)
    n_in = sum(r["exact_inside_ci95"] for r in sw["by_n"] + sw["by_p"])
    _note(fig, f"Points: simulation, {sw['by_n'][0]['trials']:,} runs each, Wilson 95% intervals. Dashed: exact values (Condorcet sum for sealed; "
          f"dynamic programme over the running tally for open). The exact value lies inside the interval at {n_in} of {len(sw['by_n']) + len(sw['by_p'])} points.")
    fig.tight_layout()
    fig.savefig(FIG / "sweep.png")
    plt.close(fig)


def fig_consensus(rows):
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    xs = [r["stubborn"] for r in rows]
    ax = axes[0]
    for r in rows:
        lo, hi = r["reached_ci95"]
        ax.bar(r["stubborn"], r["reached"], width=0.56, color=SEALED)
        ax.errorbar(r["stubborn"], r["reached"], yerr=[[max(0, r["reached"] - lo)], [max(0, hi - r["reached"])]], color=INK, capsize=3, lw=1)
        ex = consensus(r["n"], r["p"], r["stubborn"])["reached"]
        ax.plot([r["stubborn"] - 0.34, r["stubborn"] + 0.34], [ex, ex], color=INK, lw=1.2, ls=(0, (3, 2)))
        ax.text(r["stubborn"], r["reached"] + 0.04, f"{r['reached']:.2f}", ha="center", color=INK, fontsize=10, fontweight="bold")
    ax.set_xticks(xs)
    ax.set_ylim(0, 1.12)
    ax.set_xlabel("agents that never change position")
    ax.set_ylabel("share of events")
    ax.set_title(f"Unanimity within 5 sealed rounds\nN={rows[0]['n']}, p={rows[0]['p']}")
    ax.plot([], [], color=INK, lw=1.2, ls=(0, (3, 2)), label="exact")
    ax.legend(loc="upper right", fontsize=8.5)

    ax = axes[1]
    keys = sorted({k for r in rows for k in r["rounds_hist"]}, key=int)
    shades = {"1": "#BCD0F5", "2": SEALED, "5": "#C8CED9"}
    labels = {"1": "round 1", "2": "round 2", "5": "no consensus (stopped at 5)"}
    bottom = [0.0] * len(rows)
    for k in keys:
        vals = [r["rounds_hist"].get(k, 0) / r["trials"] for r in rows]
        ax.bar(xs, vals, bottom=bottom, width=0.56, color=shades.get(k, MUTED), edgecolor="white", linewidth=1.5, label=labels.get(k, f"{k} rounds"))
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_xticks(xs)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("agents that never change position")
    ax.set_title("When agreement happens\nshare of events by outcome")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8.5)
    _note(fig, f"{rows[0]['trials']:,} runs per setting through the full protocol, every round audited. Agreement can only come in round 1 or 2: "
          "after round 2 no ballot changes (see theory.consensus).")
    fig.tight_layout()
    fig.savefig(FIG / "consensus.png")
    plt.close(fig)


def main():
    FIG.mkdir(exist_ok=True)
    h = json.loads((RES / "headline.json").read_text())
    fig_headline(h)
    if (RES / "sweep.json").exists():
        fig_sweep(json.loads((RES / "sweep.json").read_text()))
    if (RES / "consensus.json").exists():
        fig_consensus(json.loads((RES / "consensus.json").read_text()))
    print("figures written to", FIG)


if __name__ == "__main__":
    main()
