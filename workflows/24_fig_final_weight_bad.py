#!/usr/bin/env python
"""Step 24 - the day-21 comparison, drawn badly on purpose.

Inputs   : data/raw/chickweight.csv
           configs/chickweight.yaml
Outputs  : figures/chickweight/final_weight_bad.png
           figures/chickweight/final_weight_bad.contract.json
Env      : bioinfo291-viz   (environment/env-viz.yml)

    python workflows/24_fig_final_weight_bad.py

This is a deliberate counterexample. It answers the same question as step 22
and breaks the contract in five ways that are individually common and
collectively fatal:

  C1  the bar baseline is at 95 g, so the 1.4x difference between the lowest
      and highest diet mean (102.6 g vs 143.0 g) is drawn as a 6.3x difference
      in bar length;
  C6  a rainbow colormap carries the group identity, and carries it alone -
      there are no tick labels, so the legend is the only way in;
  C7  the mean and the interval are computed over all 578 measurements rather
      than over the 45 chicks, treating twelve weighings of one chick as
      twelve independent observations;
  C10 the error bars are drawn with no statement of what they are;
  C12 the title asserts that a diet *improves* growth, which this
      observational comparison of unrandomised groups cannot support.

It also fails C11: the five chicks that never reach day 21 are dropped with
no mention, and the loss is not balanced across diets.

The sidecar is written by hand rather than through `save_figure`, because
`save_figure` would refuse several of these. It declares what was actually
drawn - including the inflated n - so the reviewer can be given a figure whose
own declaration is self-incriminating, which is the realistic case: authors
rarely lie about their methods, they just do not notice what the methods imply.

Nothing here should be copied. The corrected version is step 22.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def main() -> None:
    cfg = load_config("chickweight")
    P = paths().ensure()
    ds = cfg["dataset"]

    df = pd.read_csv(P.root / ds["path"])
    day = ds["final_day"]

    # C7: no aggregation to the chick. Every weighing is treated as an
    # independent observation, so n is 578 rather than 50.
    pooled = df.groupby(ds["group"])[ds["value"]]
    means = pooled.mean()
    sems = pooled.sem()
    n_rows = pooled.size()

    diets = list(means.index)
    # C6: a rainbow scale, used for an unordered categorical variable, and
    # used as the only channel that identifies a group.
    colors = plt.get_cmap("jet")(np.linspace(0, 1, len(diets)))

    fig, ax = plt.subplots(figsize=(4.2, 3.0), constrained_layout=True)
    bars = ax.bar(range(len(diets)), means.to_numpy(), color=colors, width=0.7)
    # C10: error bars with no stated definition.
    ax.errorbar(range(len(diets)), means.to_numpy(), yerr=sems.to_numpy(),
                fmt="none", ecolor="black", capsize=3)

    # C1: truncated baseline.
    ax.set_ylim(95, 150)
    ax.set_xticks([])                      # C6: no labels; the legend is all there is
    ax.set_ylabel("Weight")                # A1: no units
    ax.set_title("Diet 3 improves chick growth")   # C12: causal, unsupported
    ax.legend(bars, [f"Diet {d}" for d in diets], ncol=2)

    out = P.root / cfg["outputs"]["figures"] / "final_weight_bad.png"
    fig.savefig(out, dpi=cfg["figure"]["dpi"], bbox_inches="tight")

    # Written by hand: save_figure would reject this figure.
    sidecar = {
        "figure": out.name,
        "question": "Does final weight differ by diet?",
        "claim": ax.get_title(),
        "experimental_unit": "measurement",
        "n_per_group": {str(k): int(v) for k, v in n_rows.items()},
        "n_observations": int(len(df)),
        "error_bar": "standard error",
        "transformations": [],
        "axes": {"y": {"variable": "weight", "units": None,
                       "limits": [95, 150], "baseline_zero": False}},
        "color": {"variable": "diet", "scale": "jet",
                  "palette": "jet", "redundant_with": None},
        "excluded": "none",
        "missing": "none",
        "source_script": "workflows/24_fig_final_weight_bad.py",
        "config": "configs/chickweight.yaml",
        "git_sha": "n/a - counterexample, written by hand",
        "_note": ("Deliberate counterexample for the figure-contract review "
                  "demonstration. Not a result. See the module docstring."),
    }
    (out.with_suffix(".contract.json")).write_text(
        json.dumps(sidecar, indent=2) + "\n")

    print(f"wrote {out}")
    print(f"pooled n per diet (measurements, not chicks): {dict(n_rows)}")
    print(f"chicks actually reaching day {day}: "
          f"{df[df[ds['time']] == day][ds['experimental_unit']].nunique()}")


if __name__ == "__main__":
    main()
