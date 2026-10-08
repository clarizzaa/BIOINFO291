#!/usr/bin/env python
"""Step 03 - feature selection, Harmony batch correction, Leiden, UMAP.

Inputs   : data/processed/sadefeldman_qc.h5ad
           configs/scrnaseq.yaml  (cluster.*), configs/project.yaml (seed)
Outputs  : data/processed/sadefeldman_clustered.h5ad
           results/cluster_sizes.csv
           figures/umap_clusters.png
Env      : scrna   (environment/env-scrna.yml)

    python workflows/03_cluster.py

The matrix is already log2(TPM+1), so no normalisation or log step is applied;
doing either would double-transform the data. Scaling, PCA and the neighbour
graph run on the highly-variable subset only, which keeps peak memory near
1 GB rather than densifying all 45,692 genes.

Donor effects dominate the raw PCA of this cohort (32 patients, Smart-seq2
plates), so the embedding is corrected with Harmony on the patient label
before the graph is built. Every stochastic call takes the project seed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths, prepare_runtime, set_seed  # noqa: E402

prepare_runtime()  # must precede the scanpy import

import harmonypy  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import scanpy as sc  # noqa: E402

from plotting import (  # noqa: E402
    RESPONSE_COLORS,
    TIMEPOINT_COLORS,
    apply_style,
    embedding,
    save,
)


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths().ensure()
    seed = set_seed(cfg["random_seed"])
    cl = cfg["cluster"]
    apply_style()
    sc.settings.verbosity = 1

    adata = sc.read_h5ad(P.processed / "sadefeldman_qc.h5ad")
    print(f"loaded {adata.n_obs:,} cells x {adata.n_vars:,} genes (seed {seed})")

    # --- feature selection --------------------------------------------------
    sc.pp.highly_variable_genes(adata, n_top_genes=cl["n_top_genes"], flavor="seurat")
    n_hvg = int(adata.var["highly_variable"].sum())
    print(f"  {n_hvg} highly variable genes")

    # Work on the HVG subset; the full matrix is kept on disk for later steps.
    hvg = adata[:, adata.var["highly_variable"]].copy()
    sc.pp.scale(hvg, max_value=cl["scale_max_value"])
    sc.tl.pca(hvg, n_comps=cl["n_pcs"], svd_solver="arpack", random_state=seed)
    var_explained = float(hvg.uns["pca"]["variance_ratio"].sum())
    print(f"  PCA on {cl['n_pcs']} components explains {var_explained:.1%} of HVG variance")

    # --- batch correction over donors --------------------------------------
    print(f"  running Harmony on '{cl['batch_key']}' "
          f"({adata.obs[cl['batch_key']].nunique()} levels)")
    ho = harmonypy.run_harmony(
        hvg.obsm["X_pca"],
        hvg.obs,
        [cl["batch_key"]],
        random_state=seed,
        verbose=False,
    )
    # harmonypy >= 2.0 returns the corrected embedding as cells x components,
    # matching its input. Version 1.x returned the transpose, so the shape is
    # asserted rather than assumed: silently transposing would scramble cells.
    corrected = np.asarray(ho.Z_corr, dtype=np.float32)
    if corrected.shape != hvg.obsm["X_pca"].shape:
        corrected = corrected.T
    assert corrected.shape == hvg.obsm["X_pca"].shape, (
        f"Harmony returned {corrected.shape}, expected {hvg.obsm['X_pca'].shape}"
    )
    hvg.obsm["X_pca_harmony"] = corrected
    print(f"  Harmony finished after {len(ho.objective_harmony) - 1} iterations")

    # --- graph, clusters, embedding ----------------------------------------
    sc.pp.neighbors(hvg, use_rep="X_pca_harmony",
                    n_neighbors=cl["n_neighbors"], n_pcs=cl["n_pcs"], random_state=seed)
    sc.tl.leiden(hvg, resolution=cl["leiden_resolution"], key_added="leiden",
                 random_state=seed, flavor="igraph", n_iterations=2, directed=False)
    sc.tl.umap(hvg, random_state=seed)
    n_clusters = hvg.obs["leiden"].nunique()
    print(f"  Leiden at resolution {cl['leiden_resolution']}: {n_clusters} clusters")

    # Carry results back onto the full-gene object, which downstream steps need
    # for marker testing and pseudobulk.
    adata.obs["leiden"] = hvg.obs["leiden"].values
    adata.obsm["X_pca"] = hvg.obsm["X_pca"]
    adata.obsm["X_pca_harmony"] = hvg.obsm["X_pca_harmony"]
    adata.obsm["X_umap"] = hvg.obsm["X_umap"]
    adata.uns["pca"] = hvg.uns["pca"]
    adata.uns["cluster_params"] = {**cl, "random_seed": seed, "n_clusters": int(n_clusters)}

    sizes = (
        adata.obs.groupby("leiden", observed=True)
        .agg(n_cells=("patient", "size"),
             n_patients=("patient", "nunique"),
             n_biopsies=("biopsy", "nunique"))
        .sort_values("n_cells", ascending=False)
    )
    # A cluster drawn from very few donors is a donor effect, not a cell type.
    sizes["pct_cells"] = (100 * sizes["n_cells"] / adata.n_obs).round(2)
    sizes.to_csv(P.results / "cluster_sizes.csv")
    print(f"  wrote {P.results / 'cluster_sizes.csv'}")
    print(f"  smallest cluster {sizes['n_cells'].min()} cells; "
          f"fewest donors in a cluster {sizes['n_patients'].min()} of "
          f"{adata.obs['patient'].nunique()}")

    # --- figure -------------------------------------------------------------
    xy = adata.obsm["X_umap"]
    fig, axes = plt.subplots(1, 4, figsize=(13.6, 3.5))
    embedding(axes[0], xy, adata.obs["leiden"].astype(str),
              title=f"Leiden clusters (resolution {cl['leiden_resolution']})",
              annotate=True, seed=seed)
    embedding(axes[1], xy, adata.obs["patient"].astype(str),
              title="Patients overlap after Harmony correction", seed=seed)
    embedding(axes[2], xy, adata.obs["timepoint"].astype(str), colors=TIMEPOINT_COLORS,
              title="Timepoint", legend=True, seed=seed)
    embedding(axes[3], xy, adata.obs["response"].astype(str), colors=RESPONSE_COLORS,
              title="Response", legend=True, seed=seed)
    fig.tight_layout()
    save(fig, P.figures / "umap_clusters.png", dpi=cfg["figures"]["dpi"])

    out = P.processed / "sadefeldman_clustered.h5ad"
    adata.write_h5ad(out, compression="gzip")
    print(f"\nwrote {out}  ({out.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
