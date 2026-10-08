"""Shared figure style following the figures4papers house style.

Reference: https://github.com/ChenLiu-1996/figures4papers (scientific-figure-making skill):
sans-serif Helvetica/Arial stack, top/right spines off, frameless legends, the
blue-green-red-neutral semantic palette, tight_layout(pad=2), 300 dpi, vector PDF.

Colour semantics used throughout this survey:
  blue    -> typed decision model under study (Jev and open replicas)
  green   -> improvement after a governance control (recalibration, abstain option, ...)
  red     -> failure, attack success or comparator weakness
  neutral -> baselines, reference values, background categories
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PALETTE = {
    "blue_main": "#0F4D92",
    "blue_secondary": "#3775BA",
    "green_1": "#DDF3DE",
    "green_2": "#AADCA9",
    "green_3": "#8BCF8B",
    "red_1": "#F6CFCB",
    "red_2": "#E9A6A1",
    "red_strong": "#B64342",
    "neutral": "#CFCECE",
    "neutral_dark": "#767676",
    "ink": "#272727",
    "highlight": "#FFD700",
    "teal": "#42949E",
    "violet": "#9A4D8E",
}

DEFAULT_COLORS = [PALETTE[k] for k in ("blue_main", "green_3", "red_strong", "teal", "violet", "neutral")]

FIG_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def apply_publication_style(font_size=16, axes_linewidth=2.0):
    plt.rcParams.update({
        "font.family": ["Arial", "DejaVu Sans"],
        "font.size": font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": axes_linewidth,
        "xtick.major.width": axes_linewidth,
        "ytick.major.width": axes_linewidth,
        "legend.frameon": False,
        "svg.fonttype": "none",
        # TrueType (Type 42) fonts embed cleanly in arXiv PDFs; Type 3 does not.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def finalize_figure(fig, name, pad=2, dpi=300):
    """Save <name>.pdf (for LaTeX) and <name>.png (for previews) next to src/."""
    fig.tight_layout(pad=pad)
    out = []
    for ext in ("pdf", "png"):
        path = FIG_DIR / f"{name}.{ext}"
        fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.05, facecolor="white")
        out.append(path)
    plt.close(fig)
    for p in out:
        assert p.stat().st_size > 0, p
    return out
