"""Shared figure style for every plot in this project.

Self-contained on purpose: the repository must produce identical figures for
someone who has only the conda environment, with no editor, notebook or agent
in the loop. Workflow steps import from here so that colour, font sizes and
spine treatment cannot drift between figures.

Conventions enforced:
  * one colour per entity, reused across every figure (response groups keep
    the same two colours everywhere);
  * a three-step font ladder mapped to role, not to available space;
  * no top/right spines, no chart junk;
  * colour-vision-safe categorical pairs (no red/green oppositions).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# --- entity colours ---------------------------------------------------------
# Blue / amber: distinguishable under deuteranopia and protanopia.
RESPONSE_COLORS = {"Responder": "#1f6fb4", "Non-responder": "#d98e04"}
TIMEPOINT_COLORS = {"Pre": "#8c8c8c", "Post": "#2d6a4f"}
SORT_COLORS = {"unsorted": "#b0b0b0", "T_enriched": "#7b3294", "myeloid_enriched": "#c2561a"}
GREY = "#5a5a5a"

# Lineage palette: hue families grouped by compartment (T, NK, B, myeloid).
CELLTYPE_COLORS = {
    "CD8 memory-like": "#1f6fb4",
    "CD8 exhausted": "#0b3d66",
    "CD4 T conv": "#6baed6",
    "Treg": "#9e9ac8",
    "Cycling T": "#54278f",
    "NK": "#2d6a4f",
    "B": "#d98e04",
    "Plasma": "#8c5a0b",
    "Macrophage/Mono": "#c2561a",
    "pDC": "#e07a9a",
    "Unassigned": "#c9c9c9",
}

BASE, SMALL, TINY = 9, 8, 7


def apply_style() -> None:
    """Set the project-wide matplotlib defaults. Call before creating figures."""
    mpl.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.bbox": "tight",
            "font.size": BASE,
            "axes.titlesize": BASE,
            "axes.labelsize": BASE,
            "axes.titlelocation": "left",
            "axes.titleweight": "regular",
            "legend.fontsize": SMALL,
            "xtick.labelsize": TINY,
            "ytick.labelsize": TINY,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "svg.fonttype": "none",
        }
    )


def save(fig, path: Path | str, dpi: int = 150) -> Path:
    """Write a figure and report the path, so each step logs what it produced."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path}")
    return path


def strip_with_median(ax, groups: dict[str, np.ndarray], colors: dict[str, str],
                      seed: int, ylabel: str = "", jitter: float = 0.09) -> None:
    """Jittered raw points with a median bar.

    Used instead of a boxplot wherever n per group is small enough that the
    reader should see every observation (figure rule: show the distribution,
    not only a summary).
    """
    rng = np.random.default_rng(seed)
    for i, (name, values) in enumerate(groups.items()):
        values = np.asarray(values, dtype=float)
        values = values[np.isfinite(values)]
        x = i + rng.uniform(-jitter, jitter, size=values.size)
        ax.scatter(x, values, s=14, alpha=0.75, linewidths=0,
                   color=colors.get(name, GREY), zorder=3)
        if values.size:
            ax.hlines(np.median(values), i - 0.26, i + 0.26,
                      color=colors.get(name, GREY), lw=2.0, zorder=4)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([f"{k}\n(n={np.isfinite(np.asarray(v, dtype=float)).sum()})"
                        for k, v in groups.items()])
    ax.set_xlim(-0.6, len(groups) - 0.4)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.margins(y=0.08)


def stars(p: float) -> str:
    """Significance marker used consistently across figures."""
    if not np.isfinite(p):
        return "n/a"
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "n.s."
