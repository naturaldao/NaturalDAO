"""House style for every figure in this repository -- the single source of truth.

The rules follow the conventions distilled in the ``scientific-figure-making``
skill of ChenLiu-1996/figures4papers (https://github.com/ChenLiu-1996/figures4papers,
CC BY-NC 4.0). The rules are restated here in our own code; nothing is copied.
The full rule list, with reasons, is in docs/figure-style.md, and the short
version is in CLAUDE.md so that coding agents follow it too.

Every plotting function in this package must:

1. call :func:`apply_publication_style` (via :func:`new_figure`),
2. take colours only from :data:`PALETTE` / :data:`COND_STYLE`,
3. save only through :func:`finalize_figure` (PNG at 300 dpi + vector PDF).

``tests/test_figure_style.py`` enforces 2 and 3.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# Colour: semantic palette
# ---------------------------------------------------------------------------
# blue  = the proposal under study (PoL2)          green = positive variants / ablations of it
# red   = baselines, comparators, losses           neutral = reference / background
# highlight = one call-out per figure at most
PALETTE: dict[str, str] = {
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
    "ink_soft": "#4D4D4D",
    "ink": "#272727",
    "highlight": "#FFD700",
    "teal": "#42949E",
    "violet": "#9A4D8E",
    "white": "#FFFFFF",
    "black": "#000000",
}

DEFAULT_COLORS: tuple[str, ...] = (PALETTE["blue_main"], PALETTE["green_3"], PALETTE["red_strong"],
                                   PALETTE["teal"], PALETTE["violet"], PALETTE["neutral_dark"])

# Fixed encoding for the seven simulated conditions, identical in every figure:
# hue = mechanism family (red = Sharma et al. quadratic, grey = Sharma et al. ranked,
# blue/green = PoL2 and its ablations); dashes + hatch = 20/80 concentrated power.
COND_STYLE: dict[str, dict] = {
    "quadratic-equal":   {"color": PALETTE["red_strong"],     "ls": "-",  "hatch": "",   "marker": "o"},
    "quadratic-20/80":   {"color": PALETTE["red_strong"],     "ls": "--", "hatch": "//", "marker": "s"},
    "ranked-equal":      {"color": PALETTE["neutral_dark"],   "ls": "-",  "hatch": "",   "marker": "o"},
    "ranked-20/80":      {"color": PALETTE["neutral_dark"],   "ls": "--", "hatch": "//", "marker": "s"},
    "pol2":              {"color": PALETTE["blue_main"],      "ls": "-",  "hatch": "",   "marker": "o"},
    "pol2-no-screening": {"color": PALETTE["blue_secondary"], "ls": "-",  "hatch": "..", "marker": "^"},
    "pol2-free-talk":    {"color": PALETTE["green_3"],        "ls": "-",  "hatch": "",   "marker": "D"},
}

SEQ_CMAP = "Blues"     # magnitudes (one hue, light -> dark)
DIV_CMAP = "RdBu"      # signed differences: red = loss, white = 0, blue = gain
REF_LINE = {"color": PALETTE["black"], "alpha": 0.3, "lw": 3, "ls": "--"}
UP, DOWN = " ↑", " ↓"   # append to metric labels: higher / lower is better


# ---------------------------------------------------------------------------
# Typography and rcParams
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FigureStyle:
    font_size: int = 16          # 15-16 for compact analytic panels, 24 for large bar panels
    axes_linewidth: float = 2.0  # 2 compact, 2.5 default, 3 large bars
    font_family: tuple[str, ...] = ("Helvetica", "Arial", "Liberation Sans", "DejaVu Sans")


COMPACT = FigureStyle()
LARGE = FigureStyle(font_size=24, axes_linewidth=3.0)
CJK_FONTS = ("WenQuanYi Zen Hei", "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei",
             "PingFang SC", "SimHei")


def _mpl():
    import matplotlib

    matplotlib.use("Agg")   # headless, deterministic
    return matplotlib


def apply_publication_style(style: FigureStyle = COMPACT) -> None:
    mpl = _mpl()
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    family = [f for f in style.font_family if f in installed] or ["DejaVu Sans"]
    family += [f for f in CJK_FONTS if f in installed]   # fallback for 中文 labels
    lw = style.axes_linewidth
    mpl.rcParams.update({
        "font.family": family,
        "font.size": style.font_size,
        "axes.titlesize": style.font_size,
        "axes.labelsize": style.font_size,
        "xtick.labelsize": style.font_size - 2,
        "ytick.labelsize": style.font_size - 2,
        "legend.fontsize": style.font_size - 2,
        "axes.linewidth": lw,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.titlepad": 12,
        "axes.labelpad": 8,
        "xtick.major.width": lw * 0.75,
        "ytick.major.width": lw * 0.75,
        "xtick.major.size": 6,
        "ytick.major.size": 6,
        "lines.linewidth": 3,
        "lines.markersize": 8,
        "legend.frameon": False,
        "figure.facecolor": PALETTE["white"],
        "axes.facecolor": PALETTE["white"],
        "savefig.facecolor": PALETTE["white"],
        "svg.fonttype": "none",   # editable text in SVG
        "pdf.fonttype": 42,       # embed TrueType, editable in Illustrator
        "ps.fonttype": 42,
        "hatch.linewidth": 1.2,
    })


def new_figure(nrows: int = 1, ncols: int = 1, panel: tuple[float, float] = (5.0, 4.5),
               style: FigureStyle = COMPACT, squeeze: bool = False, **kw):
    """Apply the style and return ``(fig, axes)``; ``axes`` is a 2-D array unless squeezed.

    ``panel`` is the size of one panel in inches, so fonts stay the same size
    relative to the data in every figure.
    """
    apply_publication_style(style)
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(nrows, ncols, figsize=(panel[0] * ncols, panel[1] * nrows),
                             squeeze=squeeze, **kw)
    return fig, axes


def finalize_figure(fig, out_path: str | Path, formats: Sequence[str] = ("png", "pdf"),
                    dpi: int = 300, pad: float = 2.0, tight: bool = True) -> list[Path]:
    """The only way figures leave this package: tight layout, PNG 300 dpi + vector PDF."""
    import matplotlib.pyplot as plt

    out = Path(out_path)
    stem = out.with_suffix("") if out.suffix.lower() in {".png", ".pdf", ".svg"} else out
    stem.parent.mkdir(parents=True, exist_ok=True)
    if tight:
        fig.tight_layout(pad=pad)
    paths = []
    for fmt in formats:
        p = stem.with_suffix(f".{fmt}")
        fig.savefig(p, dpi=dpi)
        paths.append(p)
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_dark(color, threshold: float = 0.5) -> bool:
    """Perceived luminance below ``threshold`` -> put white text on it."""
    from matplotlib.colors import to_rgb

    r, g, b = to_rgb(color)
    return 0.299 * r + 0.587 * g + 0.114 * b < threshold


def ci95(p: float, n: int) -> float:
    """Half-width of a normal-approximation 95 % interval for a proportion."""
    return 1.96 * math.sqrt(max(p * (1 - p), 0.0) / n) if n > 0 else float("nan")


def plot_line(ax, x, y, name: str | None = None, color: str | None = None, ls: str | None = None,
              marker: str | None = None, err: Sequence[float] | None = None, label: str | None = None,
              alpha_band: float = 0.18, **kw):
    """Line + markers; optional symmetric uncertainty band (e.g. 95 % CI half-widths).

    ``name`` picks the condition's fixed style; explicit arguments override it
    (``marker=""`` draws no markers).
    """
    st = COND_STYLE.get(name, {}) if name else {}
    color = color or st.get("color", PALETTE["blue_main"])
    ls = ls if ls is not None else st.get("ls", "-")
    marker = marker if marker is not None else st.get("marker", "o")
    (line,) = ax.plot(x, y, color=color, ls=ls, marker=marker, label=label or name, zorder=3, **kw)
    if err is not None:
        lo = [a - e for a, e in zip(y, err)]
        hi = [a + e for a, e in zip(y, err)]
        ax.fill_between(x, lo, hi, color=color, alpha=alpha_band, lw=0, zorder=2)
    return line


def bar(ax, x, heights, name: str | None = None, color: str | None = None, hatch: str | None = None,
        width: float = 0.8, err: Sequence[float] | None = None, label: str | None = None, **kw):
    """Bars with black edges (print-safe) and optional error bars with caps."""
    st = COND_STYLE.get(name, {}) if name else {}
    color = color or st.get("color", PALETTE["blue_main"])
    hatch = st.get("hatch", "") if hatch is None else hatch
    return ax.bar(x, heights, width, color=color, hatch=hatch, edgecolor=PALETTE["black"], linewidth=1.5,
                  yerr=err, error_kw={"elinewidth": 1.5, "capthick": 1.5, "capsize": 5,
                                      "ecolor": PALETTE["ink"]},
                  label=label or name, zorder=3, **kw)


def annotate_bars(ax, bars, values: Iterable[float], fmt: str = "{:.2f}", inside: bool = False,
                  offsets: Iterable[float] | None = None, fontsize: float | None = None) -> None:
    """Print each value above its bar (or inside the top, with contrast-aware colour)."""
    offsets = list(offsets) if offsets is not None else None
    for i, (b, v) in enumerate(zip(bars, values)):
        x = b.get_x() + b.get_width() / 2
        h = b.get_height() + b.get_y()
        if inside:
            col = PALETTE["white"] if is_dark(b.get_facecolor()) else PALETTE["black"]
            ax.text(x, h - 0.02 * abs(ax.get_ylim()[1] - ax.get_ylim()[0]), fmt.format(v), ha="center",
                    va="top", color=col, fontsize=fontsize)
        else:
            off = offsets[i] if offsets else 0.0
            ax.text(x, h + off + 0.01 * abs(ax.get_ylim()[1] - ax.get_ylim()[0]), fmt.format(v),
                    ha="center", va="bottom", color=PALETTE["black"], fontsize=fontsize)


def heatmap(ax, data, x_labels: Sequence[str], y_labels: Sequence[str], cmap: str = SEQ_CMAP,
            vmin: float | None = None, vmax: float | None = None, fmt: str = "{:.2f}",
            cbar_label: str | None = None, annotate: bool = True, fontsize: float | None = None,
            colorbar: bool = True):
    """Cell heatmap with white separators, contrast-aware annotations and a labelled colorbar."""
    import matplotlib.pyplot as plt
    import numpy as np

    arr = np.asarray(data, dtype=float)
    im = ax.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", origin="lower")
    ax.set_xticks(range(len(x_labels)), x_labels)
    ax.set_yticks(range(len(y_labels)), y_labels)
    ax.set_xticks(np.arange(-0.5, arr.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, arr.shape[0], 1), minor=True)
    ax.grid(which="minor", color=PALETTE["white"], lw=1.5)
    ax.tick_params(which="minor", length=0)
    ax.tick_params(which="major", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    if annotate:
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                col = im.cmap(im.norm(arr[i, j]))
                ax.text(j, i, fmt.format(arr[i, j]), ha="center", va="center", fontsize=fontsize,
                        color=PALETTE["white"] if is_dark(col) else PALETTE["black"])
    if colorbar:
        cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
        cb.outline.set_visible(False)
        if cbar_label:
            cb.set_label(cbar_label)
    return im


def legend_panel(ax, handles, labels, **kw) -> None:
    """Dedicated legend-only axis, so legends never cover data."""
    ax.set_axis_off()
    ax.legend(handles, labels, loc=kw.pop("loc", "center"), frameon=False, **kw)


def cond_handles(names: Sequence[str], kind: str = "line"):
    """Legend handles for conditions in their fixed style."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    out = []
    for n in names:
        st = COND_STYLE[n]
        if kind == "line":
            out.append(Line2D([0], [0], color=st["color"], ls=st["ls"], marker=st["marker"], lw=3, ms=8, label=n))
        else:
            out.append(Patch(facecolor=st["color"], hatch=st["hatch"], edgecolor=PALETTE["black"], lw=1.5, label=n))
    return out
