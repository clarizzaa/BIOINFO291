#!/usr/bin/env python
"""Step 22 - what changes if we compare only the final measurement.

Inputs   : data/raw/chickweight.csv
           configs/chickweight.yaml
Outputs  : figures/final_weight.png
           figures/final_weight.contract.json
Env      : bioinfo291-viz   (environment/env-viz.yml)

    python workflows/22_fig_final_weight.py

The trajectory figure (step 21) uses every chick that was assigned to a diet.
Restricting to the last scheduled day is a *filter*, and the filter is not
balanced: chicks that stopped being weighed are not missing at random with
respect to diet, and they were the small ones. So this figure has to carry two
things at once - the day-21 comparison, and the fact that the groups being
compared lost different fractions of their chicks to get here.

Contract notes (docs/figure-contract.md):

  C7  one point per chick, never per weighing; `unit_level` collapses the 578
      measurements to one row per chick before anything is summarised;
  C9  every surviving chick is drawn, because each group is below the config
      threshold `contract.show_all_observations_below_n`;
  C10 the interval is a 95% CI over chicks, named on the figure and in the
      sidecar together with the per-group n it came from;
  C11 retained/assigned appears under every diet, so the unequal loss is
      visible in the image and not only in the sidecar;
  C12 the title states what was measured, in which chicks, and out of how
      many - it does not say a diet caused anything.

No parameter is a literal here (WORKSPACE.md rule 3); everything numeric comes
from configs/chickweight.yaml or from the data.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402
from figure_contract import (  # noqa: E402
    OKABE_ITO,
    annotate_n,
    check_palette,
    contract_caption,
    contract_style,
    save_figure,
    strip_with_units,
    unit_level,
)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Name -> palette lookup, so the config names the palette and the script does
# not hard-code the hues (C6, WORKSPACE.md rule 3).
PALETTES = {"okabe_ito": OKABE_ITO}


def main() -> None:
    cfg = load_config("chickweight")
    P = paths().ensure()
    ds, fg, ct = cfg["dataset"], cfg["figure"], cfg["contract"]
    unit, group, time, value = (
        ds["experimental_unit"], ds["group"], ds["time"], ds["value"],
    )
    day = ds["final_day"]

    df = pd.read_csv(P.root / ds["path"])

    # C7: the chick is the experimental unit. One row per chick, carrying the
    # last day on which that chick was weighed.
    last = unit_level(df, unit=unit, group=group, value=value,
                      how="last", time=time)
    assigned = last.groupby(group).size()          # denominator: every chick
    final = last[last[time] == day]                # C11: this is the filter
    retained = final.groupby(group).size()
    lost = (assigned - retained.reindex(assigned.index, fill_value=0))
    dropped = last[last[time] != day]

    diets = sorted(final[group].unique())
    colors = list(PALETTES[check_palette(fg["palette"])])[: len(diets)]

    contract_style(base_size=fg["base_font_size"], dpi=fg["dpi"])
    # One panel, drawn on the wide canvas (`figure.size_two_panel`): the
    # clauses this figure must carry in the image - n per diet (C8), the
    # interval's definition (C10) and retained/assigned (C11) - do not fit
    # legibly at `size_single_panel`. Using an existing config key rather
    # than a literal, per WORKSPACE.md rule 3.
    fig, ax = plt.subplots(figsize=tuple(fg["size_two_panel"]),
                           constrained_layout=True)

    # C9 + C10: every retained chick as a point, mean with 95% CI on top.
    n_per_group, interval_label = strip_with_units(
        ax, final, group=group, value=value, unit=unit,
        groups=diets, colors=colors, kind=ct["interval"],
    )
    if max(n_per_group.values()) > ct["show_all_observations_below_n"]:
        raise RuntimeError(
            f"a group exceeds show_all_observations_below_n="
            f"{ct['show_all_observations_below_n']}; re-check C9 before "
            f"drawing every observation"
        )

    # C8: n per group, at the chick, above each position. Must run while the
    # tick labels are still the bare group names.
    annotate_n(ax, n_per_group, unit=unit)

    # C11: the denominator of each group, under each group, in the image.
    ax.set_xticklabels([f"{g}\n{retained[g]}/{assigned[g]}" for g in diets])
    ax.set_xlabel(f"Diet\n(chicks weighed on day {day} / chicks assigned)")
    ax.set_ylabel(f"Weight on day {day} ({ds['value_units']})")

    means = final.groupby(group)[value].mean()
    hi, lo = means.idxmax(), means.idxmin()
    # A4: name the figure's main comparison, descriptively.
    ax.annotate(
        f"group means span {means[lo]:.0f}-{means[hi]:.0f} {ds['value_units']}\n"
        f"(lowest: diet {lo}; highest: diet {hi})",
        xy=(0.02, 0.97), xycoords="axes fraction", ha="left", va="top",
        fontsize=fg["base_font_size"] - 2, color="0.25",
    )
    # pad clears the per-diet 'n =' row that annotate_n writes above the axes.
    ax.set_title(
        f"Day-{day} weight by diet, in {int(retained.sum())} of "
        f"{int(assigned.sum())} chicks",
        pad=fg["base_font_size"] * 1.6,
    )

    ylim = [float(v) for v in ax.get_ylim()]
    loss_clause = "; ".join(
        f"diet {g}: {int(lost[g])} of {int(assigned[g])}" for g in assigned.index
    )
    contract = {
        "question": f"What changes if diets are compared only on the day-{day} "
                    f"weight, instead of on the whole growth trajectory?",
        "claim": ax.get_title(),
        "experimental_unit": unit,
        "n_per_group": n_per_group,
        "n_observations": f"none; each of the {int(retained.sum())} points is "
                          f"one chick's day-{day} weight",
        "error_bar": f"{interval_label}, computed per diet over the chicks "
                     f"drawn in that diet (the n printed above it)",
        "transformations": [],
        "axes": {
            "x": {"variable": group, "units": "none (4 unordered diets)",
                  "limits": [float(v) for v in ax.get_xlim()],
                  "baseline_zero": False},
            "y": {"variable": value, "units": ds["value_units"],
                  "limits": ylim, "baseline_zero": False,
                  "note": "points, not bars, so a non-zero baseline is "
                          "permitted (A2); the drawn range "
                          f"{ylim[0]:.0f}-{ylim[1]:.0f} {ds['value_units']} "
                          f"spans every displayed chick "
                          f"({final[value].min():.0f}-{final[value].max():.0f} "
                          f"{ds['value_units']})"},
        },
        "color": {"variable": group, "scale": "qualitative",
                  "palette": fg["palette"],
                  "redundant_with": "x position and x tick label"},
        "excluded": (
            f"{len(dropped)} of {int(assigned.sum())} chicks were never weighed "
            f"on day {day} and are not drawn; the loss is unequal across the "
            f"diets being compared ({loss_clause}), and retained/assigned is "
            f"printed under every diet on the figure"
        ),
        "missing": (
            f"none among the {int(retained.sum())} displayed chicks: each has "
            f"all {df[time].nunique()} scheduled weighings and every point is "
            f"an observed day-{day} measurement, none interpolated or imputed"
        ),
        "_notes": (
            f"On the excluded chicks: they were last weighed on days "
            f"{int(dropped[time].min())}-{int(dropped[time].max())} at "
            f"{int(dropped[value].min())}-{int(dropped[value].max())} "
            f"{ds['value_units']}. Those are earlier-day weights, not day-{day} "
            f"weights, so they are not comparable to the plotted values and are "
            f"not drawn; for scale, {int((final[value] < dropped[value].max()).sum())} "
            f"of the {int(retained.sum())} displayed day-{day} weights fall "
            f"below the largest of them, and the displayed weights span "
            f"{int(final[value].min())}-{int(final[value].max())} "
            f"{ds['value_units']}. The direction of the loss therefore cannot "
            f"be read off this figure; it is visible in the trajectories of "
            f"step 21. What this figure does show is that diet "
            f"{int(lost.idxmax())} contributes {int(lost.max())} fewer chicks "
            f"to the comparison than it was assigned, while diets "
            f"{', '.join(str(g) for g in assigned.index[lost == 0])} lose none."
        ),
        "source_script": "workflows/22_fig_final_weight.py",
        "config": "configs/chickweight.yaml",
    }

    caption = (
        f"Day-{day} weight of every chick weighed on day {day}; one point per "
        f"chick, horizontally jittered. " + contract_caption(contract)
    )
    # Wrap to the canvas rather than to a guessed column count: characters
    # that fit = figure width in points / (font size x mean glyph width).
    cap_size = fg["base_font_size"] - 2
    width_chars = int(fig.get_figwidth() * 72 / (cap_size * 0.56))
    fig.text(
        0, -0.01,
        "\n".join(textwrap.wrap(caption, width=width_chars)),
        ha="left", va="top", fontsize=cap_size,
    )

    out, sidecar = save_figure(fig, P.figures / "final_weight.png", contract,
                               repo=P.root)
    plt.close(fig)

    print(f"wrote {out}")
    print(f"wrote {sidecar}")
    print(f"measurements read: {len(df)}; chicks: {df[unit].nunique()}")
    print(f"chicks assigned per diet:  {dict(assigned)}")
    print(f"chicks weighed on day {day}: {dict(retained)}")
    print(f"chicks lost to the filter: {dict(lost)}")
    print(f"excluded chicks (chick, diet, last day, last weight):\n"
          f"{dropped[[unit, group, time, value]].to_string(index=False)}")
    print(f"day-{day} mean weight per diet ({ds['value_units']}): "
          f"{ {k: round(v, 1) for k, v in means.items()} }")


if __name__ == "__main__":
    main()
