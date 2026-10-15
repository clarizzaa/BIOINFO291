#!/usr/bin/env python
"""Step 32 - review figures for Wang & Horowitz 2026.

Inputs   : configs/statreview.yaml
           data/raw/papers/wang2026-conspecific-odors/Part_2.xlsx
           results/statistical_reviews/wang2026-conspecific-odors/
               pvalue_family.csv, pvalue_family_corrected_at_dog_level.csv
Outputs  : reports/statistical_reviews/wang2026-conspecific-odors/figures/
               unit_of_analysis.png      (+ .contract.json)
               what_survives.png         (+ .contract.json)
Env      : bioinfo291-stats   (environment/env-stats.yml)

docs/statistical-review.md requires at least one recomputation figure per
blocking finding. These are the two: S3/S5/S8 (the unit the Part 2 tests
counted) and S13 (the size of the test family).

    python workflows/32_fig_wang2026.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402
from figure_contract import (  # noqa: E402
    OKABE_ITO, annotate_n, contract_style, interval, interval_name, save_figure,
)

SLUG = "wang2026-conspecific-odors"
BINS = [f"{i}s" for i in range(5, 65, 5)]
COND = {"C": "blank", "J": "joy", "S": "stress"}
# The headline Part 2 claim: stress odour increased proximity to the owner.
OUTCOME_SHEET = "owner"
OUTCOME_LABEL = "Proximity to owner\n(fraction of sample points)"


def load_blocks(deposit: Path, sheet: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (per-dog frame, per-time-bin frame) for one behavioural sheet.

    The deposited sheets hold three blocks side by side. The left block is the
    raw per-dog record plus three interleaved "<condition> averages:" rows; the
    middle block (Condition, Frequency) is those average rows turned sideways,
    twelve per condition, and is what the paper's tests were run on.
    """
    raw = pd.read_excel(deposit / "Part_2.xlsx", sheet_name=sheet)

    subject = raw["Subject"].astype(str)
    dogs = raw[subject.str.startswith("Dog_")].copy()
    values = dogs[BINS].apply(pd.to_numeric, errors="coerce")
    per_dog = pd.DataFrame({
        "dog": dogs["Subject"].to_numpy(),
        "condition": [COND[o] for o in dogs["Odor"]],
        "value": values.mean(axis=1).to_numpy(),
    })

    mid = raw[["Condition", "Frequency"]].dropna()
    per_bin = pd.DataFrame({
        "bin": [f"bin{i}" for i in range(len(mid))],
        "condition": [COND[c] for c in mid["Condition"]],
        "value": mid["Frequency"].to_numpy(),
    })
    return per_dog, per_bin


def _strip(ax, df, order, colors, jitter, seed):
    """Every unit as an open marker, with the summary bar offset beside it.

    Open markers and an offset bar so the marks stay countable where values
    coincide (C4); a filled disc over a summary bar hides how many there are.
    """
    counts = {}
    rng = np.random.default_rng(seed)
    for i, grp in enumerate(order):
        vals = df.loc[df.condition == grp, "value"].to_numpy(dtype=float)
        vals = vals[~np.isnan(vals)]
        counts[grp] = int(vals.size)
        ax.scatter(i - 0.12 + rng.uniform(-jitter, jitter, vals.size), vals,
                   s=26, facecolors="none", edgecolors=colors[i], linewidths=1.1,
                   zorder=2, clip_on=False)
        mean = float(np.mean(vals))
        se = float(np.std(vals, ddof=1) / np.sqrt(vals.size))
        half = se * stats_t_crit(vals.size)
        ax.errorbar(i + 0.26, mean, yerr=half, fmt="o", color="black",
                    markersize=4, capsize=4, lw=1.4, zorder=3)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order)
    ax.set_xlim(-0.55, len(order) - 0.35)
    return counts


def stats_t_crit(n: int) -> float:
    from scipy import stats as _st
    return float(_st.t.ppf(0.975, df=n - 1))


def figure_unit_of_analysis(cfg: dict, P, deposit: Path, out_dir: Path) -> None:
    """The same comparison, drawn at the unit tested and at the unit claimed."""
    per_dog, per_bin = load_blocks(deposit, OUTCOME_SHEET)
    order = ["blank", "joy", "stress"]
    colors = OKABE_ITO[:3]

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 4.2), sharey=True)  # C2: one y scale
    fig.subplots_adjust(top=0.76, bottom=0.30, left=0.13, right=0.985, wspace=0.07)

    # WORKSPACE.md rule 4: the jitter seed is a config value, not a literal.
    seed = cfg["resampling"]["random_seed"]
    n_bins = _strip(axes[0], per_bin, order, colors, jitter=0.10, seed=seed)
    n_dogs = _strip(axes[1], per_dog, order, colors, jitter=0.10, seed=seed + 1)

    fam = pd.read_csv(P.root / cfg["outputs"]["results"] / SLUG / "pvalue_family.csv")
    row = fam.set_index("test_id").loc[f"p2.omnibus.{OUTCOME_SHEET}"]
    p_bins, p_dogs = float(row.p_published_unit), float(row.p_dog_unit)

    # C8 + A7: n carries its noun, because the two panels count different things.
    for ax, counts, noun in ((axes[0], n_bins, "bins"), (axes[1], n_dogs, "dogs")):
        for i, grp in enumerate(order):
            ax.annotate(f"n = {counts[grp]} {noun}", (i, 1.02),
                        xycoords=("data", "axes fraction"), ha="center", fontsize=7.5)

    # C10: the interval is defined inside the image, with the unit it was taken over.
    axes[0].set_title("Tested: condition mean per 5-second bin",
                      loc="left", pad=20, fontsize=8.5)
    axes[1].set_title("Claimed: one value per dog",
                      loc="left", pad=20, fontsize=8.5)
    axes[0].annotate(f"Kruskal-Wallis p = {p_bins:.1e}\nbars: mean, 95% CI over 12 time bins",
                     (0.02, 0.955), xycoords="axes fraction", ha="left", va="top",
                     fontsize=7.5)
    axes[1].annotate(f"same test, same data: p = {p_dogs:.2f}\n"
                     f"bars: mean, 95% CI over {n_dogs['blank']}/{n_dogs['joy']}/"
                     f"{n_dogs['stress']} dogs",
                     (0.02, 0.955), xycoords="axes fraction", ha="left", va="top",
                     fontsize=7.5)

    axes[0].set_ylabel("Proximity to owner\n(fraction of sample points nearest the owner)")
    for ax in axes:
        ax.set_xlabel("Odour condition")
        ax.set_ylim(0, 1.0)                             # C1: zero baseline

    # C11: the denominator and the exclusion cascade, on the figure.
    fig.text(0.015, 0.14,
             "Denominator: 11-12 coded sample points per dog (12 for 20 dogs, 11 for 4). "
             "24 of 43 recruited dogs are shown: 14 never reached Part 2, 3 discontinued, "
             "2 did not investigate the odour. The paper does not report which condition "
             "the 2 excluded dogs were assigned to, so per-group entry counts are not "
             "recoverable from the deposit.", fontsize=6.6, va="top", wrap=True)

    headline1 = ("Averaging the 24 dogs into 12 time-bin means turns "
                 f"p = {p_dogs:.2f} into p = {p_bins:.1e}")
    fig.text(0.5, 0.965, headline1, ha="center", va="top", fontsize=10)

    save_figure(fig, out_dir / "unit_of_analysis.png", {
        "question": "Does proximity to the owner differ by odour condition, and "
                    "does the answer depend on whether dogs or time bins are counted?",
        "claim": headline1,
        "experimental_unit": "dog",
        "n_per_group": n_dogs,
        "n_observations": (
            f"left panel draws the {sum(n_bins.values())} condition x time-bin means "
            f"the published tests used ({n_bins}); right panel draws one point per dog"
        ),
        "error_bar": (f"mean with 95% CI over dogs, n = {n_dogs} (right panel); "
                      "mean with 95% CI over the 12 time bins (left panel); both "
                      "definitions are printed inside the figure"),
        "transformations": ["per-dog value is the mean over that dog's coded 5-second bins"],
        "axes": {"y": {"variable": "proximity to owner",
                       "units": "fraction of the dog's coded sample points at which it "
                                "was nearest the owner",
                       "limits": [0.0, 1.0], "baseline_zero": True},
                 "x": {"variable": "odour condition", "units": "none"}},
        "shared_scales": "yes; both panels share the y axis limits and ticks",
        "color": {"variable": "odour condition", "scale": "qualitative",
                  "palette": "okabe_ito", "redundant_with": "x position and x tick label"},
        "excluded": ("of 43 recruited dogs, 14 never reached Part 2, 3 discontinued and 2 "
                     "did not investigate the odour, leaving 24 (blank 6, joy 9, stress 9); "
                     "the paper does not attribute the 2 excluded dogs to a condition, so "
                     "per-group entry counts are not recoverable and the figure says so"),
        "missing": ("4 dogs have 11 coded sample points rather than 12; those bins are "
                    "dropped from that dog's mean and the denominator is stated on the "
                    "figure"),
        "source_script": "workflows/33_fig_wang2026.py",
        "config": "configs/statreview.yaml",
    })
    plt.close(fig)


def figure_what_survives(cfg: dict, P, out_dir: Path) -> None:
    """Every reported p-value, as published and after re-analysis."""
    res = P.root / cfg["outputs"]["results"] / SLUG
    merged = pd.read_csv(res / "pvalue_family.csv")
    alpha = cfg["review"]["alpha"]
    assert len(merged) == 39, f"expected 39 reported tests, found {len(merged)}"

    merged["part"] = np.where(merged.family.str.startswith("Part 1"),
                              "Part 1: investigation time",
                              "Part 2: behaviour after exposure")
    floor = 1e-6
    merged["p_pub"] = merged.p_published_unit.clip(lower=floor)
    merged["q_cor"] = merged.BH_q_at_dog.clip(lower=floor)
    n_clipped = int((merged.p_published_unit < floor).sum() +
                    (merged.BH_q_at_dog < floor).sum())

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 4.6), sharey=True)
    fig.subplots_adjust(top=0.78, bottom=0.26, left=0.12, right=0.985, wspace=0.07)
    rng = np.random.default_rng(cfg["resampling"]["random_seed"])
    for ax, part in zip(axes, ["Part 1: investigation time",
                               "Part 2: behaviour after exposure"]):
        sub = merged[merged.part == part]
        # C4: jitter along x so coincident tests stay countable.
        jx = rng.uniform(-0.075, 0.075, len(sub))
        for (_, r), dx in zip(sub.iterrows(), jx):
            crosses = (r.p_pub < alpha) and (r.q_cor >= alpha)
            ax.plot([dx, 1 + dx], [r.p_pub, r.q_cor], lw=0.9, zorder=2,
                    color=OKABE_ITO[5] if crosses else "#9a9a9a",
                    alpha=0.95 if crosses else 0.5)
        ax.scatter(jx, sub.p_pub, s=18, facecolors="none", edgecolors="#333333",
                   linewidths=0.9, zorder=3)
        ax.scatter(1 + jx, sub.q_cor, s=18, facecolors="none", edgecolors="#333333",
                   linewidths=0.9, zorder=3)
        ax.axhline(alpha, color="black", ls="--", lw=0.9, zorder=1)
        ax.set_yscale("log")
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["p\n(as published)", "BH q\n(re-analysed)"])
        ax.set_xlim(-0.3, 1.35)
        was, kept = int((sub.p_pub < alpha).sum()), int((sub.q_cor < alpha).sum())
        ax.set_title(f"{part}\n{len(sub)} tests: {was} significant as published, "
                     f"{kept} after re-analysis", loc="left", fontsize=7.8)

    # A4: the Part 2 claim rests on one value sitting just above the line; say so.
    p2min = float(merged.loc[merged.part.str.startswith("Part 2"), "BH_q_at_dog"].min())
    axes[1].annotate(f"closest to the line: q = {p2min:.4f}", (1.0, p2min),
                     xytext=(0.06, 0.055), textcoords="axes fraction", fontsize=7,
                     arrowprops=dict(arrowstyle="->", lw=0.7, color="#333333"))

    axes[0].set_ylabel("p-value / BH q-value (log scale)")
    for ax in axes:
        ax.annotate(f"{alpha}", (0.985, alpha), xycoords=("axes fraction", "data"),
                    ha="right", va="bottom", fontsize=7, color="#333333")
    axes[0].annotate(f"{n_clipped} value(s) below {floor:g} drawn at {floor:g}",
                     (0.02, 0.985), xycoords="axes fraction", fontsize=6.8,
                     va="top", color="#555555")
    headline2 = ("Part 1's results mostly survive counting dogs and correcting the "
                 "family; Part 2's do not")
    fig.text(0.5, 0.965, headline2, ha="center", va="top", fontsize=10)
    fig.text(0.015, 0.115,
             "Orange: significant as published, not after re-analysis. "
             "39 is the number of p-values the paper reports, and a lower bound on the "
             "family: the paper additionally states that unreported comparisons and the "
             "per-pairing side-bias and time-period regressions were non-significant "
             "without giving their number, so those tests cannot be counted or corrected "
             "here.", fontsize=6.6, va="top", wrap=True)

    save_figure(fig, out_dir / "what_survives.png", {
        "question": "Which of the paper's 39 reported tests remain significant once "
                    "Part 2 is tested on dogs and the whole family is corrected?",
        "claim": headline2,
        "experimental_unit": "statistical test (one line per reported p-value)",
        "n_per_group": {"Part 1: investigation time": int((merged.part.str.startswith("Part 1")).sum()),
                        "Part 2: behaviour after exposure": int((merged.part.str.startswith("Part 2")).sum())},
        "n_observations": "none; every line is one reported test",
        "error_bar": "none; p-values and q-values are point estimates with no interval",
        "transformations": [
            "y axis is log10",
            "left column is the p-value recomputed at the unit the paper used",
            "right column is the Benjamini-Hochberg q-value over all 39 tests, with "
            "every Part 2 test recomputed at the dog level; both quantities are named "
            "on the x tick labels",
            f"{n_clipped} value(s) below {floor:g} are drawn at {floor:g}, stated on the figure",
        ],
        "axes": {"y": {"variable": "p-value (left column), BH q-value (right column)",
                       "units": "probability",
                       "limits": list(axes[0].get_ylim()), "baseline_zero": False},
                 "x": {"variable": "analysis version", "units": "none"}},
        "shared_scales": "yes; both panels share the log y axis limits and ticks",
        "color": {"variable": "whether the test stops being significant", "scale": "qualitative",
                  "palette": "okabe_ito",
                  "redundant_with": "the line's slope relative to the drawn threshold; "
                                    "one orange line is directly labelled"},
        "excluded": ("none of the reported p-values; the paper's two blanket statements "
                     "about unreported comparisons and the side-bias regressions have no "
                     "reported p-value and cannot be counted, which the figure states"),
        "missing": "none; every p-value reported in the results section is drawn",
        "source_script": "workflows/33_fig_wang2026.py",
        "config": "configs/statreview.yaml",
    })
    plt.close(fig)


def main() -> int:
    cfg = load_config("statreview")
    P = paths()
    contract_style()
    deposit = P.root / cfg["outputs"]["raw"] / SLUG
    out_dir = P.root / cfg["outputs"]["reviews"] / SLUG / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    figure_unit_of_analysis(cfg, P, deposit, out_dir)
    figure_what_survives(cfg, P, out_dir)
    print(f"wrote 2 figures and 2 sidecars to {out_dir.relative_to(P.root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
