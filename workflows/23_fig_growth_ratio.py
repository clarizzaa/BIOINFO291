#!/usr/bin/env python
"""Step 23 - absolute size or growth rate? Weight relative to each chick's own
day-0 weight, on a log2 axis.

Inputs   : data/raw/chickweight.csv
           configs/chickweight.yaml
Outputs  : figures/chickweight/growth_ratio.png
           figures/chickweight/growth_ratio.contract.json
Env      : bioinfo291-viz   (environment/env-viz.yml)

    python workflows/23_fig_growth_ratio.py

Question: is the difference between diets about absolute size, or about growth
rate?

Steps 21 and 22 plot grams. Grams confound two things a reader cannot separate
by eye: how big a chick started and how fast it grew. This step removes the
first by dividing every measurement by that chick's own day-0 weight, which is
a within-chick normalisation (C7: the chick is the unit, and each chick is its
own baseline).

Why log2 (C5). On a ratio axis a doubling from 1x to 2x and a doubling from 4x
to 8x are the same biological event but occupy wildly different distances. On
log2 they occupy exactly the same distance, so equal ratios are equally far
apart and the *slope* of a trajectory reads directly as growth rate. The
no-change reference - log2 ratio = 0, i.e. 1x - is drawn explicitly in every
panel rather than left implicit at the axis bottom.

What the normalisation hides, and how that is handled. Dividing by day 0 sets
every chick to 0 at day 0 by construction, so this figure *cannot* show a
baseline difference between diets even if one existed. That makes the
baseline a thing the reader must be told rather than shown, so the day-0
weights are stated on the figure itself (they span 39-43 g across all 50
chicks, diet means 40.7-41.4 g).

No parameter below is a literal: every threshold, size, path and column name
comes from configs/chickweight.yaml (WORKSPACE.md rule 3). The baseline day is
not hard-coded either - it is the first scheduled measurement in the data.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402
from figure_contract import (  # noqa: E402
    OKABE_ITO,
    contract_caption,
    contract_style,
    save_figure,
    trajectories_by_group,
)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def main() -> None:
    cfg = load_config("chickweight")
    P = paths().ensure()
    ds = cfg["dataset"]
    fg = cfg["figure"]
    unit, group = ds["experimental_unit"], ds["group"]
    time, value = ds["time"], ds["value"]
    final_day = ds["final_day"]

    df = pd.read_csv(P.root / ds["path"])

    # ---- C7 / C11: the baseline every chick is divided by -------------------
    # The baseline day is derived, not asserted: it is the first scheduled
    # measurement in the dataset.
    baseline_day = int(df[time].min())
    base = df[df[time] == baseline_day]
    if base[unit].duplicated().any():
        raise ValueError(f"a {unit} has more than one day-{baseline_day} measurement")

    n_entered = df.groupby(group)[unit].nunique().to_dict()
    have_base = set(base[unit])
    all_units = set(df[unit])
    without_base = sorted(all_units - have_base)
    # Every chick must have a day-0 weight before anything is divided by it.
    # If any did not, it would be excluded here and counted in the sidecar;
    # in this dataset all 50 do, so the exclusion clause is empty by fact
    # rather than by assumption.
    if without_base:
        df = df[df[unit].isin(have_base)]
    excluded_text = (
        f"every {unit} has a day-{baseline_day} weight to divide by"
        if not without_base
        else (
            f"{len(without_base)} {unit}s had no day-{baseline_day} weight and were "
            f"dropped because the ratio is undefined for them: {without_base}"
        )
    )

    w0 = base.set_index(unit)[value]
    df = df.assign(ratio=df[value] / df[unit].map(w0))
    df = df.assign(log2_ratio=np.log2(df["ratio"]))

    # ---- C11: differential loss of follow-up, counted per diet --------------
    last_day = df.groupby([unit, group])[time].max().reset_index()
    lost = (
        last_day[last_day[time] < final_day]
        .groupby(group)
        .size()
        .reindex(sorted(n_entered), fill_value=0)
        .to_dict()
    )
    n_final = (
        df[df[time] == final_day].groupby(group)[unit].nunique().reindex(sorted(n_entered)).to_dict()
    )
    # n behind the mean line falls over time wherever follow-up was lost.
    n_by_time = df.groupby([group, time])[unit].nunique()

    # ---- C9: with this few units per group, draw all of them ----------------
    threshold = cfg["contract"]["show_all_observations_below_n"]
    if max(n_entered.values()) > threshold:
        raise ValueError(
            f"a group has more than {threshold} {unit}s; C9 assumes every unit is drawn"
        )

    groups = sorted(df[group].unique())
    colors = list(OKABE_ITO[: len(groups)])

    contract_style(base_size=fg["base_font_size"], dpi=fg["dpi"])
    fig, axes, n_per_group = trajectories_by_group(
        df,
        x=time,
        y="log2_ratio",
        unit=unit,
        group=group,
        groups=groups,
        colors=colors,
        figsize=tuple(fg["size_trajectories"]),
    )

    # Median fold change at the final day, over the chicks still measured then.
    med_by_diet = df[df[time] == final_day].groupby(group)["ratio"].median()

    # ---- C5: the no-change reference, drawn, not implied --------------------
    for i, (ax, g) in enumerate(zip(axes, groups)):
        ax.axhline(0.0, color="0.25", lw=0.9, ls=(0, (4, 2)), zorder=1)
        med = med_by_diet[g]
        ax.set_title(
            f"Diet {g}\n{n_per_group[str(g)]} chicks, {n_final[g]} at day {final_day}",
            fontsize=fg["base_font_size"],
        )
        # A4: the comparison the figure exists to support, on the figure.
        ax.annotate(
            f"day {final_day}: {med:.1f}\u00d7",
            xy=(0.04, 0.96),
            xycoords="axes fraction",
            ha="left",
            va="top",
            fontsize=fg["base_font_size"] - 1,
            color=colors[i],
        )

    # Ticks name both the transformed value and the ratio it stands for, so a
    # reader never has to exponentiate by eye (C5, A1).
    lo, hi = int(np.floor(df["log2_ratio"].min())), int(np.ceil(df["log2_ratio"].max()))
    ticks = list(range(lo, hi + 1))
    axes[0].set_yticks(ticks)
    axes[0].set_yticklabels([f"{t}  ({2.0**t:g}\u00d7)" for t in ticks])
    axes[0].set_ylabel(f"log2( {value} /\nown day-{baseline_day} {value} )")
    # Sits below the reference line: the region under 0 is empty in every
    # panel, so the label cannot collide with a trajectory.
    axes[0].annotate(
        "no change (1\u00d7)",
        xy=(df[time].min(), 0.0),
        xytext=(2, -3),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=fg["base_font_size"] - 2,
        color="0.25",
    )
    for ax in axes:
        ax.set_xlabel(f"Time ({ds['time_units']})")
        ax.set_xticks(sorted(df[time].unique())[::2])

    d0_lo, d0_hi = int(base[value].min()), int(base[value].max())
    d0_means = base.groupby(group)[value].mean()
    claim = (
        f"Every chick weighed {d0_lo}-{d0_hi} g at day {baseline_day}; by day "
        f"{final_day} chicks had grown "
        f"{df.loc[df[time] == final_day, 'ratio'].min():.1f}-"
        f"{df.loc[df[time] == final_day, 'ratio'].max():.1f}\u00d7 that weight; "
        f"diet medians {med_by_diet.min():.1f}-{med_by_diet.max():.1f}\u00d7"
    )
    fig.suptitle(claim, fontsize=fg["base_font_size"] + 1)

    mean_line = (
        f"no interval is drawn. The bold line is the mean log2 ratio over the "
        f"chicks measured on that day, so its n falls where follow-up was lost "
        f"(diet 1: {n_by_time[1].iloc[0]} chicks at day {baseline_day} to "
        f"{n_final[1]} at day {final_day}; diet 4: {n_by_time[4].iloc[0]} to "
        f"{n_final[4]}; diets 2 and 3 constant). Each grey line is one chick"
    )
    contract = {
        "question": "Is the difference between diets about absolute size, or about growth rate?",
        "claim": claim,
        "experimental_unit": unit,
        "n_per_group": n_per_group,
        "n_observations": (
            f"{len(df)} measurements drawn as {sum(n_per_group.values())} per-chick "
            f"trajectories; each grey line is one chick, no mark is an independent unit"
        ),
        "error_bar": mean_line,
        "transformations": [
            f"log2( weight / that same chick's day-{baseline_day} weight ); "
            f"0 = no change (1\u00d7), drawn as a dashed line in every panel, and the "
            f"y ticks give the ratio alongside the log2 value"
        ],
        "normalisation_note": (
            f"dividing by day {baseline_day} sets every chick to 0 there by "
            f"construction, so this figure cannot show a baseline difference even "
            f"if one existed. Day-{baseline_day} weights were {d0_lo}-{d0_hi} g "
            f"overall (diet means {d0_means.min():.1f}-{d0_means.max():.1f} g), "
            f"so the normalisation removes almost no between-diet difference; the "
            f"range is stated in the title because the reader cannot see it"
        ),
        "axes": {
            "x": {
                "variable": time,
                "units": ds["time_units"],
                "limits": [int(df[time].min()), int(df[time].max())],
                "baseline_zero": True,
            },
            "y": {
                "variable": f"log2({value} / own day-{baseline_day} {value})",
                "units": "log2 ratio, dimensionless",
                "limits": [float(df["log2_ratio"].min()), float(df["log2_ratio"].max())],
                "baseline_zero": "not applicable; 0 is the no-change reference and is drawn",
            },
        },
        "shared_scales": (
            "yes; all four panels share both axes by construction "
            "(sharex=sharey=True in trajectories_by_group), identical limits and ticks, "
            "y tick labels shown once on the left panel"
        ),
        "color": {
            "variable": group,
            "scale": "qualitative",
            "palette": fg["palette"],
            "redundant_with": "panel position and panel title; colour marks only the mean line",
        },
        "excluded": (
            f"nothing: all {len(all_units)} chicks and all {len(df)} measurements "
            f"are drawn, and {excluded_text}. Follow-up ended before day {final_day} for "
            + ", ".join(f"{v} of {n_entered[k]} on diet {k}" for k, v in lost.items())
            + " - that loss is differential across diets, so those trajectories "
            "simply stop and the panel titles give both counts"
        ),
        "missing": (
            "no interior measurements are missing; every chick was weighed at every "
            "scheduled day up to its last. Chicks whose follow-up ended early have a "
            "line that stops there and is not extended or imputed"
        ),
        "source_script": "workflows/23_fig_growth_ratio.py",
        "config": "configs/chickweight.yaml",
    }

    caption = (
        "Each chick's weight divided by its own day-"
        f"{baseline_day} weight, on a log2 axis, one panel per diet. "
        + contract_caption(contract)
    )
    fig.text(
        0.0,
        -0.02,
        caption,
        ha="left",
        va="top",
        fontsize=fg["base_font_size"] - 3,
        wrap=True,
        transform=fig.transFigure,
    )

    out = P.root / cfg["outputs"]["figures"] / "growth_ratio.png"
    png, sidecar = save_figure(fig, out, contract, repo=P.root)
    print(f"wrote {png.relative_to(P.root)}")
    print(f"wrote {sidecar.relative_to(P.root)}")
    print(f"chicks per diet (experimental unit): {n_per_group}")
    print(f"chicks measured at day {final_day}: {n_final}")
    print(f"day-{baseline_day} weight range: {d0_lo}-{d0_hi} g")


if __name__ == "__main__":
    main()
