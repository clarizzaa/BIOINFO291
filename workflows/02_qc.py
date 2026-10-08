#!/usr/bin/env python
"""Step 02 - quality control, with the count of objects removed by each filter.

Inputs   : data/processed/sadefeldman_raw.h5ad
           configs/scrnaseq.yaml  (qc.*)
Outputs  : data/processed/sadefeldman_qc.h5ad
           results/qc_counts.csv
           figures/qc_metrics.png
Env      : scrna   (environment/env-scrna.yml)

    python workflows/02_qc.py

The matrix is log2(TPM+1), not counts, so scanpy's default QC metrics do not
apply: `total_counts` has no meaning for a library already normalised to a
fixed sum, and a mitochondrial percentage computed on log values is not a
percentage of anything. Mitochondrial content is therefore computed in linear
TPM space (2**x - 1, which maps 0 to 0 and so preserves sparsity) as

    100 * sum(TPM over MT- genes) / sum(TPM over all genes)

The authors released an already-curated CD45+ set, having applied their own
per-cell quality filters, so only extreme mitochondrial content is removed
here. The gene-detection threshold in the config is reported for inspection
but deliberately not applied; see DECISIONS.md.
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

from plotting import GREY, RESPONSE_COLORS, apply_style, save  # noqa: E402


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths().ensure()
    seed = set_seed(cfg["random_seed"])
    qc = cfg["qc"]
    apply_style()

    adata = sc.read_h5ad(P.processed / "sadefeldman_raw.h5ad")
    print(f"loaded {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    # --- per-cell metrics ---------------------------------------------------
    # Genes detected: any non-zero entry.
    adata.obs["n_genes"] = np.asarray((adata.X > 0).sum(axis=1)).ravel()

    # Mitochondrial fraction in linear TPM space.
    linear = adata.X.copy()
    linear.data = np.expm1(linear.data * np.log(2.0)).astype(np.float32)  # 2**x - 1
    is_mito = np.asarray(adata.var_names.str.startswith(qc["mito_prefix"]))
    total = np.asarray(linear.sum(axis=1)).ravel()
    mito = np.asarray(linear[:, is_mito].sum(axis=1)).ravel()
    del linear
    with np.errstate(invalid="ignore", divide="ignore"):
        adata.obs["pct_mito"] = np.where(total > 0, 100.0 * mito / total, 0.0)
    print(f"  {int(is_mito.sum())} mitochondrial genes matched '{qc['mito_prefix']}*'")
    print(f"  median genes/cell {np.median(adata.obs['n_genes']):.0f}; "
          f"median pct_mito {np.median(adata.obs['pct_mito']):.1f}%")

    # --- figure before filtering -------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(9.4, 2.9))
    axes[0].hist(adata.obs["n_genes"], bins=60, color=GREY)
    axes[0].axvline(qc["reference_min_genes"], color="#b02418", lw=1.2, ls="--")
    axes[0].set_xlabel("genes detected per cell")
    axes[0].set_ylabel("cells")
    axes[0].set_title("All cells clear the usual 200-gene floor")
    axes[0].annotate(f"{qc['reference_min_genes']} genes\n(not applied)",
                     xy=(qc["reference_min_genes"], axes[0].get_ylim()[1] * 0.72),
                     xytext=(8, 0), textcoords="offset points", fontsize=7, color="#b02418")

    axes[1].hist(adata.obs["pct_mito"], bins=60, color=GREY)
    axes[1].axvline(qc["max_pct_mito"], color="#b02418", lw=1.2, ls="--")
    axes[1].set_xlabel("mitochondrial TPM (%)")
    axes[1].set_ylabel("cells")
    axes[1].set_title("A small tail exceeds the mitochondrial cutoff")
    axes[1].annotate(f"cutoff {qc['max_pct_mito']}%",
                     xy=(qc["max_pct_mito"], axes[1].get_ylim()[1] * 0.78),
                     xytext=(8, 0), textcoords="offset points", fontsize=7, color="#b02418")

    for resp, color in RESPONSE_COLORS.items():
        sub = adata.obs.loc[adata.obs["response"] == resp]
        axes[2].scatter(sub["n_genes"], sub["pct_mito"], s=2, alpha=0.3,
                        linewidths=0, color=color, label=resp)
    axes[2].axhline(qc["max_pct_mito"], color="#b02418", lw=1.2, ls="--")
    axes[2].set_xlabel("genes detected per cell")
    axes[2].set_ylabel("mitochondrial TPM (%)")
    # The title states the measured loss per group rather than asserting
    # balance: the difference is small but not nil (see results/qc_counts.csv).
    loss = (
        adata.obs.assign(fail=adata.obs["pct_mito"] >= qc["max_pct_mito"])
        .groupby("response", observed=True)["fail"]
        .mean()
        .mul(100)
    )
    axes[2].set_title(
        "Cells lost to the cutoff: "
        + ", ".join(f"{v:.1f}% {k.lower()}" for k, v in loss.items())
    )
    leg = axes[2].legend(markerscale=4, loc="upper right", handletextpad=0.3)
    for h in leg.legend_handles:
        h.set_alpha(1.0)
    fig.tight_layout()
    save(fig, P.figures / "qc_metrics.png", dpi=cfg["figures"]["dpi"])

    # --- filters, counting at every step ------------------------------------
    rows = []

    def record(stage: str, a, note: str) -> None:
        rows.append({"stage": stage, "n_cells": a.n_obs, "n_genes": a.n_vars, "note": note})
        print(f"  {stage:28s} cells={a.n_obs:>6,}  genes={a.n_vars:>6,}  {note}")

    record("00_loaded", adata, "as released by the authors")

    keep_cells = (adata.obs["pct_mito"] < qc["max_pct_mito"]).to_numpy()
    n_drop = int((~keep_cells).sum())
    adata = adata[keep_cells].copy()
    record("01_mito_filter", adata, f"removed {n_drop} cells with >={qc['max_pct_mito']}% mito TPM")

    n_before = adata.n_vars
    sc.pp.filter_genes(adata, min_cells=qc["min_cells_per_gene"])
    record("02_gene_filter", adata,
           f"removed {n_before - adata.n_vars} genes in <{qc['min_cells_per_gene']} cells")

    counts = pd.DataFrame(rows)
    counts["cells_removed"] = -counts["n_cells"].diff().fillna(0).astype(int)
    counts["genes_removed"] = -counts["n_genes"].diff().fillna(0).astype(int)
    counts.to_csv(P.results / "qc_counts.csv", index=False)
    print(f"  wrote {P.results / 'qc_counts.csv'}")

    # Cells surviving per biopsy: the statistics later need a minimum per sample.
    per_biopsy = adata.obs.groupby("biopsy", observed=True).size()
    print(f"  cells per biopsy after QC: min {per_biopsy.min()}, "
          f"median {int(per_biopsy.median())}, max {per_biopsy.max()}")

    adata.uns["qc"] = {k: v for k, v in qc.items()}
    adata.uns["random_seed"] = seed
    out = P.processed / "sadefeldman_qc.h5ad"
    adata.write_h5ad(out, compression="gzip")
    print(f"\nwrote {out}  ({out.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
