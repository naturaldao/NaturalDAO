"""Enforce the figure rules in docs/figure-style.md and CLAUDE.md."""

import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "pol2dao"
PLOTTING = [SRC / "figures.py", *sorted((SRC / "experiments").glob("*.py"))]


def test_only_plotstyle_saves_figures():
    offenders = [p.name for p in SRC.rglob("*.py") if p.name != "plotstyle.py" and "savefig(" in p.read_text()]
    assert offenders == [], f"save through plotstyle.finalize_figure, not savefig: {offenders}"


def test_no_hard_coded_colours_outside_the_palette():
    hexes = re.compile(r"['\"]#[0-9A-Fa-f]{6}['\"]")
    offenders = {p.name: hexes.findall(p.read_text()) for p in PLOTTING if hexes.search(p.read_text())}
    assert offenders == {}, f"take colours from plotstyle.PALETTE: {offenders}"


def test_publication_rcparams():
    pytest.importorskip("matplotlib")
    import matplotlib

    from pol2dao.plotstyle import COMPACT, apply_publication_style

    apply_publication_style()
    rc = matplotlib.rcParams
    assert rc["axes.spines.top"] is False and rc["axes.spines.right"] is False
    assert rc["legend.frameon"] is False and rc["axes.grid"] is False
    assert rc["font.size"] == COMPACT.font_size and rc["axes.linewidth"] == COMPACT.axes_linewidth
    assert rc["pdf.fonttype"] == 42 and rc["svg.fonttype"] == "none"


def test_condition_styles_are_complete_and_print_safe():
    from pol2dao.plotstyle import COND_STYLE, PALETTE
    from pol2dao.simulate import CONDITIONS

    assert {c.name for c in CONDITIONS} <= set(COND_STYLE)
    for name, st in COND_STYLE.items():
        assert st["color"] in PALETTE.values(), name
        if "20/80" in name:   # concentrated power is encoded redundantly
            assert st["ls"] == "--" and st["hatch"], name


def test_finalize_writes_png_and_pdf(tmp_path):
    pytest.importorskip("matplotlib")
    from pol2dao.plotstyle import finalize_figure, new_figure, plot_line

    fig, axes = new_figure(1, 1)
    plot_line(axes[0][0], [0, 1, 2], [0.1, 0.5, 0.4], "pol2", err=[0.05, 0.05, 0.05])
    paths = finalize_figure(fig, tmp_path / "x.png")
    assert sorted(p.suffix for p in paths) == [".pdf", ".png"] and all(p.exists() for p in paths)
