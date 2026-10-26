"""Render task-specific, non-pooled plots from the audited v1.3 summary."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
SUMMARY = HERE / "runs-20261026-v1.3" / "summary.json"
OUT = HERE / "runs-20261026-v1.3" / "typed_knowledge_results.png"

TASKS = [
    ("Definition → concept", "definition_to_concept", "concepts_relations"),
    ("Directed relation completion", "directed_relation_completion", "concepts_relations"),
    ("Axiom component identification", "axiom_component_identification", "axioms_propositions"),
    ("Proposition source attribution", "proposition_source_attribution", "axioms_propositions"),
    ("Love language identification", "definition_to_love_language", "love_languages"),
    ("Review question → rule", "review_question_to_rule", "explicit_governance_rules"),
    ("Interpretation provenance retrieval", "interpretation_provenance_retrieval", "researcher_interpretations"),
]
MODELS = [("qwen2.5:7b", "Qwen 2.5 7B", "#167D9A"), ("llama3.1:8b", "Llama 3.1 8B", "#C15A3B")]
CONDITIONS = [("closed_book", "Closed book", "o"), ("source_context", "Source excerpts", "s")]


def main() -> None:
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    lookup = {(r["model"], r["condition"], r["knowledge_type"]): r for r in data["runs"]}
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
        "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#AAB4BE", "xtick.color": "#45515D", "ytick.color": "#27323B",
        "text.color": "#17212B", "axes.labelcolor": "#45515D",
        "savefig.facecolor": "white",
    })
    fig, axs = plt.subplots(4, 2, figsize=(11.2, 10.0), sharex=True, constrained_layout=True)
    axs = axs.ravel()
    offsets = {"qwen2.5:7b": 0.20, "llama3.1:8b": -0.20}
    for i, (title, task, typ) in enumerate(TASKS):
        ax = axs[i]
        ax.set_title(title, loc="left", fontweight="semibold", pad=9)
        ax.set_xlim(-3, 103)
        ax.set_ylim(-0.56, 0.56)
        ax.set_yticks([])
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.grid(axis="x", color="#E7EBEF", linewidth=0.8, zorder=0)
        ax.axvline(50, color="#C9D1D8", linewidth=0.8, zorder=0)
        for model, label, color in MODELS:
            pts = []
            ns = []
            for cond, _, _marker in CONDITIONS:
                run = lookup[(model, cond, typ)]
                metric = run["by_type_and_task"][task]
                pts.append(100 * metric["exact_match_rate"])
                ns.append(metric["n_expected"])
            y = offsets[model]
            ax.plot(pts, [y, y], color=color, linewidth=1.6, alpha=0.75, zorder=2)
            ax.scatter(pts[0], y, s=42, marker="o", facecolor="white", edgecolor=color,
                       linewidth=1.5, zorder=3)
            ax.scatter(pts[1], y, s=44, marker="s", facecolor=color, edgecolor="white",
                       linewidth=0.6, zorder=3)
            crowded = abs(pts[0] - pts[1]) < 11
            if crowded:
                ax.annotate(f"{pts[0]:.0f}%", (pts[0], y), xytext=(0, 11),
                            textcoords="offset points", ha="right" if pts[0] > 95 else "center", va="center", color=color,
                            fontsize=8, fontweight="semibold")
                ax.annotate(f"{pts[1]:.0f}%", (pts[1], y), xytext=(0, -13),
                            textcoords="offset points", ha="right" if pts[1] > 95 else "center", va="center", color=color,
                            fontsize=8, fontweight="semibold")
            else:
                for x in set(pts):
                    ax.annotate(f"{x:.0f}%", (x, y), xytext=(0, 9 if y > 0 else -14),
                                textcoords="offset points", ha="right" if x > 95 else "center", va="center", color=color,
                                fontsize=8, fontweight="semibold")
            ax.text(-0.02, y, label, transform=ax.get_yaxis_transform(), ha="right", va="center",
                    color=color, fontsize=8, clip_on=False)
        n = lookup[("qwen2.5:7b", "closed_book", typ)]["by_type_and_task"][task]["n_expected"]
        ax.text(1.0, 0.94, f"n = {n}", transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color="#697681")
        if typ == "explicit_governance_rules":
            ax.text(0.99, 0.06, "See status-stratified table in report", transform=ax.transAxes,
                    ha="right", va="bottom", fontsize=7, color="#697681")
    axs[-1].set_visible(False)
    axs[4].set_xlabel("Exact-match accuracy (%)")
    axs[5].set_xlabel("Exact-match accuracy (%)")
    from matplotlib.lines import Line2D
    legend = [
        Line2D([0], [0], color="#637381", marker="o", markerfacecolor="white", lw=1.3,
               label="Closed book"),
        Line2D([0], [0], color="#637381", marker="s", markerfacecolor="#637381", lw=1.3,
               label="Source excerpts"),
        Line2D([0], [0], color=MODELS[0][2], lw=2, label=MODELS[0][1]),
        Line2D([0], [0], color=MODELS[1][2], lw=2, label=MODELS[1][1]),
    ]
    fig.legend(handles=legend, loc="outside upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.02), fontsize=8)
    fig.suptitle("PoL2 typed-knowledge pilot: exact-match accuracy by task", y=1.075,
                 fontsize=14, fontweight="bold", color="#17212B")
    fig.text(0.5, -0.015,
             "Public exploratory set; labels are source-derived. No pooled score. Rule results are stratified separately.",
             ha="center", va="top", fontsize=8, color="#596773")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=240, bbox_inches="tight")
    print(OUT)


if __name__ == "__main__":
    main()
