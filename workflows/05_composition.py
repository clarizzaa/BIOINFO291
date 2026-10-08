#!/usr/bin/env python
"""Step 05 - confounding checks, then composition testing at the patient level.

Inputs   : data/processed/sadefeldman_annotated.h5ad
           configs/scrnaseq.yaml  (composition.*)
Outputs  : results/confounding_check.csv
           results/sample_proportions.csv
           results/patient_proportions.csv
           results/composition_stats.csv
           figures/composition_barplots.png
           figures/composition_boxplots.png
Env      : scrna   (environment/env-scrna.yml)

    python workflows/05_composition.py

The confounding table is written first and deliberately: therapy regimen,
timepoint, FACS sorting fraction and cells sequenced per sample are each
tested against response before any composition result is read, because a
compositional difference that tracks a sorting gate is not biology.

Unit of analysis. Response in GSE120575 is recorded per biopsy, not per
patient: 48 biopsies come from 32 patients and four patients carry
contradictory labels across their own lesions. Cells from one patient are not
independent replicates, so the primary test averages each patient's biopsy
proportions into a single observation and drops the four patients with no
defined patient-level label. The biopsy-level test the reference example used
is computed alongside, so the cost of the correction is visible rather than
asserted.

The Pre/Post contrast is paired: eleven patients were biopsied at both
timepoints, and a signed-rank test on those pairs removes the between-patient
variance that swamps an unpaired comparison.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths, prepare_runtime, set_seed  # noqa: E402

prepare_runtime()  # must precede the scanpy import

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import scanpy as sc  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.stats.multitest import multipletests  # noqa: E402

from plotting import (  # noqa: E402
    CELLTYPE_COLORS,
    RESPONSE_COLORS,
    apply_style,
    save,
    stars,
    strip_with_median,
)


def confounding_table(meta: pd.DataFrame) -> pd.DataFrame:
    """Test each candidate confounder against response, at biopsy level."""
    rows = []
    for var in ("therapy", "timepoint", "sort_fractions"):
        ct = pd.crosstab(meta[var], meta["response"])
        chi2, p, dof, _ = stats.chi2_contingency(ct)
        rows.append({
            "variable": var, "test": "chi-square", "statistic": round(float(chi2), 3),
            "dof": int(dof), "p": float(p), "n_biopsies": int(ct.to_numpy().sum()),
            "detail": "; ".join(f"{i}: " + "/".join(str(v) for v in ct.loc[i])
                                for i in ct.index),
        })
    r = meta.loc[meta.response == "Responder", "n_cells"]
    nr = meta.loc[meta.response == "Non-responder", "n_cells"]
    u, p = stats.mannwhitneyu(r, nr)
    rows.append({
        "variable": "n_cells_per_biopsy", "test": "Mann-Whitney",
        "statistic": round(float(u), 3), "dof": np.nan, "p": float(p),
        "n_biopsies": len(meta),
        "detail": f"median Responder {r.median():.0f} vs Non-responder {nr.median():.0f}",
    })
    # Repeated sampling of the same patient is itself a structural issue.
    per_patient = meta.groupby("patient", observed=True).size()
    rows.append({
        "variable": "biopsies_per_patient", "test": "none (structural)",
        "statistic": np.nan, "dof": np.nan, "p": np.nan, "n_biopsies": len(meta),
        "detail": f"{len(per_patient)} patients; "
                  + "; ".join(f"{int(k)} biopsies: {int(v)} patients"
                              for k, v in per_patient.value_counts().sort_index().items()),
    })
    return pd.DataFrame(rows)


def test_groups(frame: pd.DataFrame, group: pd.Series, populations: list[str],
                a: str, b: str, unit: str, comparison: str,
                method: str) -> pd.DataFrame:
    """Unpaired comparison of each population's proportion between two groups."""
    rows = []
    for pop in populations:
        xa = frame.loc[group == a, pop].dropna().to_numpy()
        xb = frame.loc[group == b, pop].dropna().to_numpy()
        if len(xa) < 3 or len(xb) < 3:
            continue
        u, p = stats.mannwhitneyu(xa, xb)
        rows.append({
            "comparison": comparison, "unit": unit, "test": method,
            "population": pop, "group_a": a, "group_b": b,
            "n_a": len(xa), "n_b": len(xb),
            "median_a": round(float(np.median(xa)), 4),
            "median_b": round(float(np.median(xb)), 4),
            "statistic": float(u), "p": float(p),
        })
    return pd.DataFrame(rows)


def test_paired(wide_pre: pd.DataFrame, wide_post: pd.DataFrame,
                populations: list[str], unit: str, comparison: str) -> pd.DataFrame:
    """Paired Post-vs-Pre comparison within patients biopsied at both times."""
    rows = []
    shared = wide_pre.index.intersection(wide_post.index)
    for pop in populations:
        pre = wide_pre.loc[shared, pop].to_numpy()
        post = wide_post.loc[shared, pop].to_numpy()
        ok = np.isfinite(pre) & np.isfinite(post)
        if ok.sum() < 3 or np.allclose(pre[ok], post[ok]):
            continue
        w, p = stats.wilcoxon(post[ok], pre[ok])
        rows.append({
            "comparison": comparison, "unit": unit, "test": "Wilcoxon signed-rank",
            "population": pop, "group_a": "Post", "group_b": "Pre",
            "n_a": int(ok.sum()), "n_b": int(ok.sum()),
            "median_a": round(float(np.median(post[ok])), 4),
            "median_b": round(float(np.median(pre[ok])), 4),
            "statistic": float(w), "p": float(p),
        })
    return pd.DataFrame(rows)


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths().ensure()
    seed = set_seed(cfg["random_seed"])
    comp = cfg["composition"]
    apply_style()

    adata = sc.read_h5ad(P.processed / "sadefeldman_annotated.h5ad")
    obs = adata.obs
    populations = [c for c in CELLTYPE_COLORS if c in set(obs["cell_type"])]
    print(f"loaded {adata.n_obs:,} cells, {len(populations)} populations")

    # --- biopsy metadata and the confounding check --------------------------
    meta = (
        obs.groupby("biopsy", observed=True)
        .agg(patient=("patient", "first"), timepoint=("timepoint", "first"),
             response=("response", "first"), therapy=("therapy", "first"),
             n_cells=("patient", "size"),
             sort_fractions=("sort_fraction", lambda s: "+".join(sorted(set(s)))))
    )
    conf = confounding_table(meta)
    conf.to_csv(P.results / "confounding_check.csv", index=False)
    print(f"  wrote {P.results / 'confounding_check.csv'}")
    for _, r in conf.iterrows():
        flag = "" if not np.isfinite(r["p"]) else ("  <-- associated" if r["p"] < 0.05 else "")
        print(f"    {r['variable']:22s} p={r['p'] if np.isfinite(r['p']) else float('nan'):.3g}{flag}")

    # --- proportions per biopsy --------------------------------------------
    counts = (
        obs.groupby(["biopsy", "cell_type"], observed=True).size()
        .unstack(fill_value=0).reindex(columns=populations, fill_value=0)
    )
    keep = counts.sum(axis=1) >= comp["min_cells_per_sample"]
    print(f"  {int((~keep).sum())} biopsies below {comp['min_cells_per_sample']} cells excluded")
    counts = counts[keep]
    props = counts.div(counts.sum(axis=1), axis=0)
    props = props.join(meta[["patient", "timepoint", "response", "therapy", "n_cells"]])
    props.to_csv(P.results / "sample_proportions.csv")

    # --- aggregate to the patient ------------------------------------------
    consistent = (
        props.groupby("patient", observed=True)["response"].nunique() == 1
    )
    inconsistent = sorted(consistent.index[~consistent])
    print(f"  {len(inconsistent)} patients excluded from the patient-level "
          f"response test (contradictory labels): {', '.join(inconsistent)}")

    patient = props.groupby("patient", observed=True)[populations].mean()
    patient["response"] = props.groupby("patient", observed=True)["response"].agg(
        lambda s: s.iloc[0] if s.nunique() == 1 else "Inconsistent"
    )
    patient["n_biopsies"] = props.groupby("patient", observed=True).size()
    patient.to_csv(P.results / "patient_proportions.csv")

    pat_ok = patient[patient["response"] != "Inconsistent"] \
        if comp["drop_label_inconsistent_patients"] else patient
    print(f"  patient-level n = {len(pat_ok)} "
          f"({(pat_ok.response == 'Responder').sum()} Responder, "
          f"{(pat_ok.response == 'Non-responder').sum()} Non-responder)")

    # --- the tests ----------------------------------------------------------
    results = [
        test_groups(pat_ok, pat_ok["response"], populations,
                    "Responder", "Non-responder", "patient",
                    "Responder vs Non-responder", "Mann-Whitney"),
        test_groups(props, props["response"], populations,
                    "Responder", "Non-responder", "biopsy",
                    "Responder vs Non-responder", "Mann-Whitney"),
    ]

    # Paired timepoint contrast within patients biopsied twice.
    pre = props[props.timepoint == "Pre"].groupby("patient", observed=True)[populations].mean()
    post = props[props.timepoint == "Post"].groupby("patient", observed=True)[populations].mean()
    n_paired = len(pre.index.intersection(post.index))
    print(f"  {n_paired} patients have both a Pre and a Post biopsy (paired test)")
    results.append(test_paired(pre, post, populations, "patient", "Post vs Pre (paired)"))
    results.append(
        test_groups(props, props["timepoint"], populations, "Post", "Pre",
                    "biopsy", "Post vs Pre (unpaired)", "Mann-Whitney")
    )

    # Sensitivity: drop the FACS-enriched biopsies entirely.
    unsorted_only = props[meta.loc[props.index, "sort_fractions"].to_numpy() == "unsorted"]
    pat_unsorted = unsorted_only.groupby("patient", observed=True)[populations].mean()
    pat_unsorted["response"] = unsorted_only.groupby("patient", observed=True)["response"].agg(
        lambda s: s.iloc[0] if s.nunique() == 1 else "Inconsistent"
    )
    pat_unsorted = pat_unsorted[pat_unsorted["response"] != "Inconsistent"]
    print(f"  sensitivity analysis excluding FACS-enriched biopsies: "
          f"n = {len(pat_unsorted)} patients")
    results.append(
        test_groups(pat_unsorted, pat_unsorted["response"], populations,
                    "Responder", "Non-responder", "patient (unsorted biopsies only)",
                    "Responder vs Non-responder", "Mann-Whitney")
    )

    stats_df = pd.concat(results, ignore_index=True)
    # Correct within each comparison x unit family, not across all of them.
    stats_df["padj"] = np.nan
    for key, idx in stats_df.groupby(["comparison", "unit"], observed=True).groups.items():
        stats_df.loc[idx, "padj"] = multipletests(
            stats_df.loc[idx, "p"], method=comp["multiple_testing"]
        )[1]
    stats_df["significant"] = stats_df["padj"] < comp["alpha"]

    # --- CD8 memory : exhausted ratio ---------------------------------------
    num, den = comp["ratio_numerator"], comp["ratio_denominator"]
    ratio_rows = []
    for frame, unit in ((pat_ok, "patient"), (props, "biopsy")):
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = frame[num] / frame[den].replace(0, np.nan)
        a = ratio[frame["response"] == "Responder"].dropna()
        b = ratio[frame["response"] == "Non-responder"].dropna()
        u, p = stats.mannwhitneyu(a, b)
        ratio_rows.append({
            "comparison": "Responder vs Non-responder", "unit": unit,
            "test": "Mann-Whitney", "population": f"{num} : {den} ratio",
            "group_a": "Responder", "group_b": "Non-responder",
            "n_a": len(a), "n_b": len(b),
            "median_a": round(float(a.median()), 4), "median_b": round(float(b.median()), 4),
            "statistic": float(u), "p": float(p), "padj": float(p),
            "significant": bool(p < comp["alpha"]),
        })
    stats_df = pd.concat([stats_df, pd.DataFrame(ratio_rows)], ignore_index=True)
    stats_df.to_csv(P.results / "composition_stats.csv", index=False)
    print(f"  wrote {P.results / 'composition_stats.csv'}")

    primary = stats_df[(stats_df.unit == "patient")
                       & (stats_df.comparison == "Responder vs Non-responder")]
    print("\nprimary comparison (patient level):")
    print(primary[["population", "n_a", "n_b", "median_a", "median_b", "p", "padj"]]
          .round(4).to_string(index=False))

    # --- figures ------------------------------------------------------------
    # Stacked mean composition per group: the overview.
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.4), sharey=True)
    for ax, (key, groups) in zip(
        axes, [("response", ["Responder", "Non-responder"]), ("timepoint", ["Pre", "Post"])]
    ):
        frame = props.groupby(key, observed=True)[populations].mean().reindex(groups)
        bottom = np.zeros(len(frame))
        for pop in populations:
            ax.bar(range(len(frame)), frame[pop].to_numpy(), bottom=bottom, width=0.62,
                   color=CELLTYPE_COLORS[pop], label=pop, linewidth=0)
            bottom += frame[pop].to_numpy()
        ax.set_xticks(range(len(frame)))
        ax.set_xticklabels([f"{g}\n(n={int((props[key] == g).sum())} biopsies)" for g in groups])
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("mean fraction of cells")
    axes[0].set_title("Composition shifts with response")
    axes[1].set_title("Composition barely shifts with timepoint")
    axes[1].legend(loc="center left", bbox_to_anchor=(1.02, 0.5), labelspacing=0.3)
    fig.tight_layout()
    save(fig, P.figures / "composition_barplots.png", dpi=cfg["figures"]["dpi"])

    # Per-population patient-level distributions: the tested quantity.
    show = [p for p in populations]
    ncol = 5
    nrow = int(np.ceil((len(show) + 1) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(2.3 * ncol, 2.5 * nrow))
    axes = np.atleast_1d(axes).ravel()
    lookup = primary.set_index("population")
    for ax, pop in zip(axes, show):
        groups = {g: pat_ok.loc[pat_ok.response == g, pop].to_numpy()
                  for g in ("Responder", "Non-responder")}
        strip_with_median(ax, groups, RESPONSE_COLORS, seed=seed)
        padj = lookup.loc[pop, "padj"] if pop in lookup.index else np.nan
        ax.set_title(f"{pop}\n{stars(padj)}  padj={padj:.3f}" if np.isfinite(padj) else pop)
        ax.set_ylabel("fraction of cells" if ax is axes[0] else "")
    # Final panel: the memory-to-exhausted ratio.
    ax = axes[len(show)]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = pat_ok[num] / pat_ok[den].replace(0, np.nan)
    strip_with_median(ax, {g: ratio[pat_ok.response == g].dropna().to_numpy()
                           for g in ("Responder", "Non-responder")},
                      RESPONSE_COLORS, seed=seed)
    rrow = [r for r in ratio_rows if r["unit"] == "patient"][0]
    ax.set_title(f"CD8 memory : exhausted\n{stars(rrow['p'])}  p={rrow['p']:.3f}")
    ax.set_ylabel("ratio")
    for ax in axes[len(show) + 1:]:
        ax.axis("off")
    fig.suptitle(
        f"Per-patient population fractions, Responder vs Non-responder "
        f"(n={len(pat_ok)} patients; Mann-Whitney, BH-adjusted)",
        y=1.005, x=0.01, ha="left",
    )
    fig.tight_layout()
    save(fig, P.figures / "composition_boxplots.png", dpi=cfg["figures"]["dpi"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
