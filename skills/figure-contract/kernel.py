"""Helpers for the figure contract (docs/figure-contract.md).

Each function exists to make one rule cheap to obey. Rule identifiers in the
docstrings refer to that file; the skill and the review subagent cite the same
identifiers.

Self-contained on purpose: a clean checkout of this repository reproduces
every figure without any platform-provided skill.
"""

import json
import math
import os
import subprocess
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Okabe-Ito: eight hues distinguishable under the common forms of colour
# vision deficiency. Qualitative only - never use for ordered magnitude (C6).
OKABE_ITO = (
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # bluish green
    "#CC79A7",  # reddish purple
    "#56B4E9",  # sky blue
    "#D55E00",  # vermillion
    "#F0E442",  # yellow
    "#000000",  # black
)

# Perceptually uniform, monotone in lightness. Safe for ordered magnitude (C6).
SEQUENTIAL = "viridis"

# Diverging, requires an explicit centre (C6).
DIVERGING = "RdBu_r"

# Scales that invent boundaries in a smooth field. Rejected by check_palette.
BANNED_COLORMAPS = ("jet", "rainbow", "gist_rainbow", "hsv", "nipy_spectral", "turbo")

# Filled in by save_figure; the author does not supply them.
SIDECAR_AUTO = ("figure", "git_sha")

# The author must supply all of these. See docs/figure-contract.md, 'The
# sidecar'. Use an explicit "none" rather than omitting a field: a figure that
# excludes nothing should say so.
SIDECAR_REQUIRED = (
    "question",
    "claim",
    "experimental_unit",
    "n_per_group",
    "n_observations",
    "error_bar",
    "transformations",
    "axes",
    "color",
    "excluded",
    "missing",
    "source_script",
    "config",
)

# Required only when it applies, and checked at save time: a figure with more
# than one panel must declare whether those panels share their scales (C2).
SIDECAR_CONDITIONAL = ("shared_scales",)


def contract_style(base_size=9, dpi=300):
    """Minimal styling floor. Not a rule - legibility only.

    Kept small deliberately: this skill governs what a figure promises, not
    how it looks. Everything here is a default that any script may override.
    """
    mpl.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": dpi,
            "savefig.bbox": "tight",
            "font.size": base_size,
            "axes.titlesize": base_size + 1,
            "axes.labelsize": base_size,
            "xtick.labelsize": base_size - 1,
            "ytick.labelsize": base_size - 1,
            "legend.fontsize": base_size - 1,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "axes.prop_cycle": mpl.cycler(color=list(OKABE_ITO)),
        }
    )


def check_palette(name):
    """C6 - refuse colormaps that invent boundaries in a smooth field."""
    if str(name).lower().rstrip("_r") in BANNED_COLORMAPS:
        raise ValueError(
            f"{name!r} is a rainbow scale: it creates apparent rings in smooth "
            f"data (C6). Use {SEQUENTIAL!r} for ordered magnitude or "
            f"{DIVERGING!r} with an explicit centre for diverging values."
        )
    return name


def unit_level(df, unit, group, value, how="last", time=None):
    """C7 - collapse repeated measurements to one row per experimental unit.

    Call this before any summary, interval, or test. `how` is 'last' (the
    final measurement, requires `time`), 'mean', or 'max'.

    Returns a frame with one row per unit, carrying its group label.
    """
    g = df.groupby([unit, group], observed=True)
    if how == "last":
        if time is None:
            raise ValueError("how='last' needs the name of the time column")
        idx = g[time].idxmax()
        out = df.loc[idx, [unit, group, time, value]].reset_index(drop=True)
    elif how == "mean":
        out = g[value].mean().reset_index()
    elif how == "max":
        out = g[value].max().reset_index()
    else:
        raise ValueError(f"unknown how={how!r}")
    return out


def is_missing(x):
    try:
        return math.isnan(float(x))
    except (TypeError, ValueError):
        return False


INTERVAL_NAMES = {
    "SD": "mean \u00b1 SD",
    "SE": "mean \u00b1 SE",
    "CI95": "mean with 95% CI",
}


def interval_name(kind):
    """C10 - the definition of an interval, without any n attached.

    Use this whenever one figure shows several groups: an n belongs to a
    group, not to the figure, and a single trailing 'n = 9' misdescribes
    every group but the last.
    """
    try:
        return INTERVAL_NAMES[kind]
    except KeyError:
        raise ValueError(f"unknown interval kind={kind!r}") from None


def interval(values, kind="CI95"):
    """C10 - return a summary together with the words that define it.

    Returns (centre, half_width, label). The label names the interval and
    the n it came from, so it is correct only for a single group; for a
    multi-group figure use `interval_name` plus per-group counts.
    """
    v = np.asarray([x for x in values if x is not None and not is_missing(x)], dtype=float)
    n = v.size
    if n < 2:
        raise ValueError(f"interval needs at least 2 observations, got {n}")
    mean = float(v.mean())
    sd = float(v.std(ddof=1))
    if kind == "SD":
        return mean, sd, f"mean \u00b1 SD, n = {n}"
    sem = sd / math.sqrt(n)
    if kind == "SE":
        return mean, sem, f"mean \u00b1 SE, n = {n}"
    if kind == "CI95":
        from scipy import stats

        t = float(stats.t.ppf(0.975, n - 1))
        return mean, t * sem, f"mean with 95% CI, n = {n}"
    raise ValueError(f"unknown interval kind={kind!r}")


def annotate_n(ax, counts, unit, y=1.02):
    """C8 - print n per group, at the experimental unit, above each position.

    `counts` maps the tick label to the number of units.
    """
    labels = [t.get_text() for t in ax.get_xticklabels()]
    for i, lab in enumerate(labels):
        if lab in counts:
            ax.text(
                i,
                y,
                f"n = {counts[lab]}",
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=mpl.rcParams["font.size"] - 1,
            )
    return ax


def line_with_gaps(ax, x, y, **kw):
    """C4 - draw a series so unmeasured points become visible gaps.

    Missing values are preserved as NaN rather than dropped, so matplotlib
    breaks the line instead of interpolating across the hole.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray([np.nan if v is None else v for v in y], dtype=float)
    order = np.argsort(x)
    return ax.plot(x[order], y[order], **kw)


def trajectories_by_group(
    df,
    x,
    y,
    unit,
    group,
    groups=None,
    colors=None,
    figsize=(7.2, 2.2),
    unit_alpha=0.45,
    unit_lw=0.7,
):
    """C2 + C7 + C9 - one panel per group, shared scales, every unit drawn.

    Individual units are light and subordinate; the group mean is drawn on
    top in the group's colour. Panels share both axes by construction, so the
    rule cannot be broken by forgetting to set limits.

    Returns (fig, axes, n_per_group).
    """
    groups = list(groups) if groups is not None else sorted(df[group].unique())
    colors = list(colors) if colors is not None else list(OKABE_ITO[: len(groups)])
    fig, axes = plt.subplots(
        1, len(groups), figsize=figsize, sharex=True, sharey=True,
        constrained_layout=True,
    )
    axes = np.atleast_1d(axes)
    n_per_group = {}
    for ax, g, c in zip(axes, groups, colors):
        sub = df[df[group] == g]
        units = sub[unit].unique()
        n_per_group[str(g)] = int(len(units))
        for u in units:
            s = sub[sub[unit] == u]
            line_with_gaps(ax, s[x], s[y], color="0.55", lw=unit_lw, alpha=unit_alpha)
        m = sub.groupby(x, observed=True)[y].mean()
        line_with_gaps(ax, m.index, m.values, color=c, lw=2.0)
        ax.set_title(f"{group} {g}  (n = {len(units)})")
    for ax in axes[1:]:
        ax.tick_params(labelleft=False)
    return fig, axes, n_per_group


def strip_with_units(ax, df, group, value, unit, groups=None, colors=None, kind="CI95"):
    """C9 + C10 - every experimental unit as a point, with a named interval.

    Returns (n_per_group, interval_label).
    """
    groups = list(groups) if groups is not None else sorted(df[group].unique())
    colors = list(colors) if colors is not None else list(OKABE_ITO[: len(groups)])
    rng = np.random.default_rng(0)
    n_per_group = {}
    label = interval_name(kind)
    for i, (g, c) in enumerate(zip(groups, colors)):
        v = df.loc[df[group] == g, value].to_numpy(dtype=float)
        n_per_group[str(g)] = int(v.size)
        ax.scatter(
            i + rng.uniform(-0.12, 0.12, v.size), v, s=16, color=c, alpha=0.75,
            edgecolor="none", zorder=2,
        )
        centre, half, _ = interval(v, kind=kind)
        ax.errorbar(
            i, centre, yerr=half, fmt="_", color="black", markersize=18,
            lw=1.4, capsize=4, zorder=3,
        )
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([str(g) for g in groups])
    ax.set_xlim(-0.6, len(groups) - 0.4)
    if any(n < 2 for n in n_per_group.values()):
        raise ValueError(f"a group has fewer than 2 units: {n_per_group}")
    return n_per_group, label


def git_sha(repo=None):
    """Commit the figure was generated at; flags an unclean tree."""
    repo = Path(repo) if repo else Path(__file__).resolve().parents[2]
    # Pin the config out: a provenance stamp must not depend on whatever the
    # local or global gitconfig happens to say, and a sandboxed kernel may be
    # unable to read ~/.gitconfig at all.
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)

    def _git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, check=True, env=env,
        ).stdout.strip()

    try:
        sha = _git("rev-parse", "--short", "HEAD")
        return f"{sha}-dirty" if _git("status", "--porcelain") else sha
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def contract_caption(contract):
    """Build the caption clauses the contract requires (C5, C8, C10, C11).

    Returns a string the script appends to its own descriptive sentence.
    """
    parts = []
    n = contract.get("n_per_group") or {}
    if n:
        unit = contract["experimental_unit"]
        inner = "; ".join(f"{k}: {v}" for k, v in n.items())
        parts.append(f"n = {sum(n.values())} {unit}s ({inner})")
    eb = contract.get("error_bar")
    if eb and eb != "none":
        parts.append(str(eb))
    for t in contract.get("transformations") or []:
        parts.append(str(t))
    for key in ("excluded", "missing"):
        v = contract.get(key)
        if v and v != "none":
            parts.append(str(v))
    return ". ".join(parts) + "." if parts else ""


def save_figure(fig, path, contract, repo=None):
    """The only sanctioned way to write a figure. Validates, then saves both.

    Writes `path` and its sidecar `path.with_suffix('.contract.json')`.
    Refuses to write anything if the declaration is incomplete, so a figure
    cannot exist in this repository without stating what it promises.
    """
    path = Path(path)
    absent = [f for f in SIDECAR_REQUIRED if f not in contract]
    if absent:
        raise ValueError(
            "sidecar is incomplete; cannot save. Missing: "
            + ", ".join(absent)
            + ". See docs/figure-contract.md, 'The sidecar'."
        )
    if not contract.get("n_per_group"):
        raise ValueError("n_per_group is empty: state n at the experimental unit (C8)")
    if len(fig.axes) > 1 and "shared_scales" not in contract:
        raise ValueError(
            "this figure has more than one panel, so it must declare "
            "'shared_scales' (C2)"
        )
    contract = dict(contract)
    contract["figure"] = path.name
    contract["git_sha"] = git_sha(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    sidecar = path.with_suffix(".contract.json")
    sidecar.write_text(json.dumps(contract, indent=2, sort_keys=False) + "\n")
    return path, sidecar
