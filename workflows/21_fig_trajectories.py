#!/usr/bin/env python
"""Step 21 - growth trajectories by diet, every chick drawn.

Inputs   : data/raw/chickweight.csv
           configs/chickweight.yaml
Outputs  : figures/chickweight/trajectories.png
           figures/chickweight/trajectories.contract.json
Env      : bioinfo291-viz   (environment/env-viz.yml)

    python workflows/21_fig_trajectories.py

Question: how do growth trajectories differ across diets, and how consistent
are those patterns across individual chicks?

Contract notes (docs/figure-contract.md):

  C2  one panel per diet, built by `trajectories_by_group` with
      sharex=sharey=True, so the four panels cannot drift apart.
  C4  each chick is reindexed onto the full scheduled day grid before
      plotting, so an unmeasured day is NaN and the line breaks instead of
      interpolating. The five chicks whose measurements stop early end in an
      x marker, so a short line reads as "weighing stopped", not "weight
      stopped changing".
  C7  the unit is the chick. The grey lines are the units; the coloured line
      is their mean, and it is the only summary drawn.
  C9  n per diet is at or below the config threshold for showing every
      observation, so every chick is drawn rather than summarised. The script
      asserts this rather than assuming it.
  C11 the mean is over chicks measured on that day, and its denominator falls
      when a chick stops. It is drawn solid while every chick of the diet is
      still being weighed and dashed afterwards, and each panel states how
      many chicks were weighed on the final day.

No parameter is a literal here; everything comes from configs/chickweight.yaml
(WORKSPACE.md rule 3).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib as mpl  # noqa: E402
import pandas as pd  # noqa: E402

from figure_contract import (  # noqa: E402
    OKABE_ITO,
    contract_style,
    line_with_gaps,
    save_figure,
    trajectories_by_group,
)

PALETTES = {"okabe_ito": OKABE_ITO}


def on_full_time_grid(df, unit, group, time, value, grid):
    """C4 - give every unit a row for every scheduled day, NaN where unmeasured.

    Dropping an unmeasured day lets the line close over the hole; keeping it
    as NaN makes the hole visible. Returns the reindexed frame and the number
    of unmeasured days that fall *inside* a unit's own observed range.
    """
    frames, interior = [], 0
    for (u, g), s in df.groupby([unit, group], observed=True):
        full = (
            s.set_index(time)
            .reindex(grid)
            .assign(**{unit: u, group: g})
            .rename_axis(time)
            .reset_index()
        )
        interior += int(full.loc[full[time] <= s[time].max(), value].isna().sum())
        frames.append(full)
    return pd.concat(frames, ignore_index=True), interior


def main() -> None:
    cfg = load_config("chickweight")
    P = paths().ensure()
    ds, fg, ct = cfg["dataset"], cfg["figure"], cfg["contract"]
    unit, group = ds["experimental_unit"], ds["group"]
    time, value = ds["time"], ds["value"]
    final_day = ds["final_day"]

    contract_style(base_size=fg["base_font_size"], dpi=fg["dpi"])
    colors = PALETTES[fg["palette"]]

    df = pd.read_csv(P.root / ds["path"])
    grid = sorted(df[time].unique())
    diets = sorted(df[group].unique())

    # C7/C8: n is the number of chicks, never the number of weighings.
    n_chicks = df.groupby(group)[unit].nunique().to_dict()
    n_final = df[df[time] == final_day].groupby(group)[unit].nunique().to_dict()
    mean_final = (
        df[df[time] == final_day].groupby(group)[value].mean().round(0).astype(int)
    )

    # C9: drawing every unit is a config decision, not a habit.
    assert max(n_chicks.values()) <= ct["show_all_observations_below_n"], (
        f"{max(n_chicks.values())} chicks in the largest diet exceeds the "
        f"show-all threshold {ct['show_all_observations_below_n']}; this figure "
        "would need a summary form"
    )

    gridded, interior_gaps = on_full_time_grid(df, unit, group, time, value, grid)

    # Last day each chick was weighed, and the chicks that stop before the end.
    last = (
        df.sort_values(time)
        .groupby([unit, group], observed=True)
        .last()
        .reset_index()[[unit, group, time, value]]
    )
    stopped = last[last[time] < final_day].sort_values([group, time])

    fig, axes, n_per_group = trajectories_by_group(
        gridded, x=time, y=value, unit=unit, group=group,
        groups=diets, colors=colors[: len(diets)],
        figsize=tuple(fg["size_trajectories"]),
    )

    small = mpl.rcParams["xtick.labelsize"]
    for ax, diet, color in zip(axes, diets, colors):
        sub = gridded[gridded[group] == diet]
        # The mean's denominator: how many chicks of this diet were weighed
        # on each day. Solid while it is complete, dashed once it is not (C11).
        per_day = sub.groupby(time, observed=True)[value].agg(["mean", "count"])
        complete = per_day["count"] == n_chicks[diet]
        last_complete = per_day.index[complete].max()
        mean_line = [ln for ln in ax.lines if ln.get_linewidth() > 1][-1]
        full_part = per_day.loc[per_day.index <= last_complete]
        mean_line.set_data(full_part.index.to_numpy(), full_part["mean"].to_numpy())
        thin_part = per_day.loc[per_day.index >= last_complete]
        if len(thin_part) > 1:
            line_with_gaps(
                ax, thin_part.index, thin_part["mean"],
                color=color, lw=mean_line.get_linewidth(), ls="--",
            )

        # C4: a short line ends in a marker, so it reads as "weighing stopped".
        ends = stopped[stopped[group] == diet]
        ax.scatter(ends[time], ends[value], marker="x", s=18, color="0.25",
                   linewidths=0.9, zorder=3)

        # C8/C11 in the panel, not only in the caption.
        ax.set_title(f"Diet {diet} \u2014 {n_chicks[diet]} chicks")
        ax.text(
            0.04, 0.96,
            f"day {final_day}: {n_final[diet]}/{n_chicks[diet]} weighed\n"
            f"mean {mean_final[diet]} {ds['value_units']}",
            transform=ax.transAxes, ha="left", va="top", fontsize=small,
        )
        ax.set_xlabel(f"Time ({ds['time_units']})")
        ax.set_xticks(grid[::2])
    axes[0].set_ylabel(f"Weight ({ds['value_units']})")

    lo, hi = mean_final.idxmin(), mean_final.idxmax()
    claim = (
        f"Weight of every chick from hatch to day {final_day} on four diets; "
        f"mean day-{final_day} weight ranged from {mean_final[lo]} "
        f"{ds['value_units']} (diet {lo}) to {mean_final[hi]} "
        f"{ds['value_units']} (diet {hi})"
    )
    fig.suptitle(claim, fontsize=fg["base_font_size"] + 1)

    stop_text = "; ".join(
        f"chick {int(r[unit])} (diet {int(r[group])}) day {int(r[time])}"
        for _, r in stopped.iterrows()
    )
    footer = (
        f"Grey: one chick. Coloured: mean of the chicks weighed that day "
        f"\u2014 solid while all chicks of the diet were still weighed, dashed "
        f"after the first stops. No error bars. \u00d7 marks a chick's last "
        f"weighing: {stop_text}. Unmeasured days are gaps, not interpolated "
        f"({interior_gaps} missing days inside an observed range). "
        f"No chick or measurement excluded; all {len(df)} weighings of "
        f"{df[unit].nunique()} chicks are drawn."
    )
    fig.text(0.0, -0.02, footer, ha="left", va="top", fontsize=small, wrap=True)

    y_lo, y_hi = axes[0].get_ylim()
    out = P.root / cfg["outputs"]["figures"] / "trajectories.png"
    png, sidecar = save_figure(fig, out, {
        "question": ("How do growth trajectories differ across diets, and how "
                     "consistent are those patterns across individual chicks?"),
        "claim": claim,
        "experimental_unit": unit,
        "n_per_group": n_per_group,
        "n_observations": int(len(df)),
        "error_bar": ("none; the coloured line is the arithmetic mean weight "
                      "of the chicks weighed on that day, not an interval"),
        "transformations": [],
        "axes": {
            "x": {"variable": time, "units": ds["time_units"],
                  "limits": [float(grid[0]), float(grid[-1])],
                  "baseline_zero": True},
            "y": {"variable": value, "units": ds["value_units"],
                  "limits": [round(float(y_lo), 1), round(float(y_hi), 1)],
                  "baseline_zero": False},
        },
        "shared_scales": {
            "shared": True, "axes": ["x", "y"],
            "detail": (f"{len(diets)} panels built with sharex=sharey=True; "
                       f"identical limits and ticks, y labelled on the left "
                       f"panel only"),
        },
        "color": {
            "variable": group, "scale": "qualitative", "palette": fg["palette"],
            "redundant_with": ("panel position and panel title; individual "
                               "chicks are grey in every panel"),
        },
        "excluded": (
            "none; no chick, weighing, or timepoint was filtered. Denominator "
            f"of the day-{final_day} mean per diet: "
            + ", ".join(f"{d}: {n_final[d]}/{n_chicks[d]}" for d in diets)
            + " chicks weighed, because five chicks stop earlier"
        ),
        "missing": (
            "Each chick is reindexed onto the full scheduled day grid "
            f"({', '.join(str(g) for g in grid)}), so an unmeasured day is NaN "
            "and the line breaks rather than interpolating; "
            f"{interior_gaps} such days fall inside a chick's observed range. "
            "Five chicks are not weighed through to day "
            f"{final_day} ({stop_text}); each of those lines ends at its last "
            "weighing and is marked with an x, so a short line reads as "
            "measurement stopping rather than weight plateauing. The diet mean "
            "is dashed over the days when its denominator is below the diet's "
            "full chick count."
        ),
        "source_script": "workflows/21_fig_trajectories.py",
        "config": "configs/chickweight.yaml",
    })

    print(f"wrote {png}")
    print(f"wrote {sidecar}")
    print(f"chicks per diet: {n_chicks}")
    print(f"chicks weighed at day {final_day}: {n_final}")
    print(f"mean weight at day {final_day} ({ds['value_units']}): "
          f"{mean_final.to_dict()}")
    print(f"chicks stopping before day {final_day}: {stop_text}")
    print(f"missing days inside an observed range: {interior_gaps}")
    print(f"weighings drawn: {len(df)} of {len(df)}")


if __name__ == "__main__":
    main()
