#!/usr/bin/env python
"""Step 04 - label Leiden clusters as immune lineages and CD8 states.

Inputs   : data/processed/sadefeldman_clustered.h5ad
           configs/scrnaseq.yaml  (annotation.*)
Outputs  : data/processed/sadefeldman_annotated.h5ad
           results/cluster_markers.csv
           results/cluster_annotation.csv
           figures/umap_celltypes.png
           figures/marker_heatmap.png
           figures/marker_dotplot.png
Env      : scrna   (environment/env-scrna.yml)

    python workflows/04_annotate.py

Labels are assigned to clusters, not to individual cells. For each cluster the
mean expression of every marker panel is z-scored across clusters, and the
cluster takes the highest-scoring panel provided it clears
`annotation.min_lineage_score`; otherwise it stays "Unassigned". Nothing is
labelled by eye, so changing a panel in the config changes the annotation.

CD8 clusters are then split into memory-like and exhausted/dysfunctional by
comparing the two state panels within the CD8 clusters only. The reference
example made this split per cell; doing it per cluster keeps the unit of
annotation the same as the unit the graph actually resolved, and avoids
drawing a hard boundary through what is a continuum at the single-cell level.
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

from plotting import CELLTYPE_COLORS, apply_style, embedding, save  # noqa: E402


def cluster_means(adata, genes: list[str], key: str = "leiden") -> pd.DataFrame:
    """Mean log2(TPM+1) per cluster for a small set of genes (clusters x genes)."""
    present = [g for g in genes if g in adata.var_names]
    sub = adata[:, present]
    dense = np.asarray(sub.X.todense()) if hasattr(sub.X, "todense") else np.asarray(sub.X)
    df = pd.DataFrame(dense, columns=present, index=adata.obs[key].astype(str).values)
    return df.groupby(level=0, observed=True).mean()


def panel_scores(means: pd.DataFrame, panels: dict[str, list[str]],
                 subset: pd.Index | None = None) -> pd.DataFrame:
    """Mean z-score of each panel's genes, per cluster.

    ``subset`` restricts both the z-scoring and the output to a set of
    clusters. Calibrating within the clusters still in contention is what
    makes two panels comparable: a score standardised over every cluster in
    the dataset is dominated by between-compartment variation, so e.g. the
    exhaustion panel always outscores the memory panel among T cells.
    """
    m = means if subset is None else means.loc[subset]
    z = (m - m.mean(axis=0)) / m.std(axis=0).replace(0, np.nan)
    out = {}
    for name, genes in panels.items():
        cols = [g for g in genes if g in z.columns]
        if not cols:
            raise SystemExit(f"no genes of panel '{name}' present in the data")
        out[name] = z[cols].mean(axis=1)
    return pd.DataFrame(out)


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths().ensure()
    seed = set_seed(cfg["random_seed"])
    ann = cfg["annotation"]
    apply_style()
    sc.settings.verbosity = 1

    adata = sc.read_h5ad(P.processed / "sadefeldman_clustered.h5ad")
    n_clusters = adata.obs["leiden"].nunique()
    print(f"loaded {adata.n_obs:,} cells in {n_clusters} clusters")

    # --- marker genes per cluster ------------------------------------------
    sc.tl.rank_genes_groups(adata, groupby="leiden", method=ann["marker_test"])
    markers = sc.get.rank_genes_groups_df(adata, group=None)
    markers = (
        markers.sort_values(["group", "pvals_adj", "scores"], ascending=[True, True, False])
        .groupby("group", observed=True)
        .head(ann["n_markers_reported"])
    )
    markers.to_csv(P.results / "cluster_markers.csv", index=False)
    print(f"  wrote {P.results / 'cluster_markers.csv'} "
          f"({ann['n_markers_reported']} genes x {n_clusters} clusters)")

    # --- hierarchical cluster labelling -------------------------------------
    thr = ann["thresholds"]
    all_panel_genes = sorted(
        {g for genes in ann["compartments"].values() for g in genes}
        | {g for genes in ann["lymphoid"].values() for g in genes}
        | {g for genes in ann["cd8_states"].values() for g in genes}
    )
    means = cluster_means(adata, all_panel_genes)

    # Level 1: compartment.
    comp = panel_scores(means, ann["compartments"])
    label = comp.idxmax(axis=1).where(comp.max(axis=1) >= thr["min_compartment_z"], "Unassigned")

    # Level 2: subsets inside the T compartment, calibrated on T clusters only.
    # Applied in increasing order of specificity so the more specific call wins.
    tcells = label.index[label == "T"]
    lym = panel_scores(means, ann["lymphoid"], subset=tcells)
    sub = pd.Series("CD4 T conv", index=tcells, dtype=object)
    sub[lym["cd8"] > lym["cd4"]] = "CD8 T"
    sub[lym["treg"] >= thr["treg_z"]] = "Treg"
    sub[lym["cycling"] >= thr["cycling_z"]] = "Cycling T"
    label.loc[tcells] = sub
    print(f"  {len(tcells)} T clusters resolved into {sub.value_counts().to_dict()}")

    # Level 3: CD8 state, calibrated on the CD8 clusters only.
    cd8 = label.index[label == "CD8 T"]
    states = panel_scores(means, ann["cd8_states"], subset=cd8)
    label.loc[cd8] = np.where(states["memory"] >= states["exhausted"],
                              "CD8 memory-like", "CD8 exhausted")
    print(f"  {len(cd8)} CD8 clusters split into "
          f"{int((label == 'CD8 memory-like').sum())} memory-like and "
          f"{int((label == 'CD8 exhausted').sum())} exhausted")

    annotation = pd.DataFrame({
        "cell_type": label,
        "compartment_score": comp.max(axis=1).round(3),
        "n_cells": adata.obs.groupby("leiden", observed=True).size(),
    })
    annotation.index.name = "leiden"
    annotation = (
        annotation.join(comp.round(3).add_prefix("comp_"))
        .join(lym.round(3).add_prefix("lym_"))
        .join(states.round(3).add_prefix("cd8state_"))
    )
    annotation.to_csv(P.results / "cluster_annotation.csv")
    print(f"  wrote {P.results / 'cluster_annotation.csv'}")

    adata.obs["cell_type"] = (
        adata.obs["leiden"].astype(str).map(label).astype("category")
    )
    if adata.obs["cell_type"].isna().any():
        raise SystemExit("some clusters were not assigned a label")

    counts = adata.obs["cell_type"].value_counts()
    print("\ncells per population:")
    print((counts.to_frame("n_cells").assign(pct=(100 * counts / adata.n_obs).round(1))).to_string())

    # --- figures ------------------------------------------------------------
    xy = adata.obsm["X_umap"]
    # The T-cell populations are intermingled at the centre of the embedding,
    # so centroid labels collide; a legend keys them without overprinting.
    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    embedding(ax, xy, adata.obs["cell_type"].astype(str), colors=CELLTYPE_COLORS,
              title="Immune populations in 48 melanoma biopsies",
              legend=True, size=2.2, seed=seed)
    fig.tight_layout()
    save(fig, P.figures / "umap_celltypes.png", dpi=cfg["figures"]["dpi"])

    display = [g for g in ann["display_markers"] if g in adata.var_names]
    order = [c for c in CELLTYPE_COLORS if c in set(adata.obs["cell_type"])]
    ct_means = cluster_means(adata, display, key="cell_type").reindex(order)
    zed = ((ct_means - ct_means.mean(axis=0)) / ct_means.std(axis=0).replace(0, np.nan))

    fig, ax = plt.subplots(figsize=(0.30 * len(display) + 2.4, 0.38 * len(order) + 1.9))
    im = ax.imshow(zed.to_numpy(), cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set_xticks(range(len(display)))
    ax.set_xticklabels(display, rotation=90, style="italic")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.set_title("Canonical markers separate the annotated populations")
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.62, pad=0.02)
    cb.set_label("mean expression, z-scored across populations", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    fig.tight_layout()
    save(fig, P.figures / "marker_heatmap.png", dpi=cfg["figures"]["dpi"])

    # Dot plot: colour is mean expression, size is the fraction of cells with
    # any detected expression, which the heatmap alone cannot show.
    sub = adata[:, display]
    dense = np.asarray(sub.X.todense()) if hasattr(sub.X, "todense") else np.asarray(sub.X)
    frame = pd.DataFrame(dense, columns=display, index=adata.obs["cell_type"].astype(str).values)
    frac = frame.gt(0).groupby(level=0, observed=True).mean().reindex(order)

    fig, ax = plt.subplots(figsize=(0.30 * len(display) + 2.6, 0.38 * len(order) + 1.9))
    gx, gy = np.meshgrid(np.arange(len(display)), np.arange(len(order)))
    sct = ax.scatter(gx.ravel(), gy.ravel(), s=(frac.to_numpy().ravel() * 70),
                     c=zed.to_numpy().ravel(), cmap="RdBu_r", vmin=-2, vmax=2,
                     edgecolors="none")
    ax.set_xticks(range(len(display)))
    ax.set_xticklabels(display, rotation=90, style="italic")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.set_xlim(-0.6, len(display) - 0.4)
    ax.set_ylim(len(order) - 0.4, -0.6)
    ax.set_title("Marker expression and the fraction of cells detecting it")
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(sct, ax=ax, shrink=0.62, pad=0.02)
    cb.set_label("mean expression, z-scored", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    for f in (0.25, 0.5, 1.0):
        ax.scatter([], [], s=f * 70, c="#777777", label=f"{int(f * 100)}%")
    ax.legend(title="cells detecting", loc="center left", bbox_to_anchor=(1.14, 0.5),
              labelspacing=0.9, title_fontsize=7, fontsize=7)
    fig.tight_layout()
    save(fig, P.figures / "marker_dotplot.png", dpi=cfg["figures"]["dpi"])

    adata.uns["annotation_params"] = {**thr, "marker_test": ann["marker_test"]}
    out = P.processed / "sadefeldman_annotated.h5ad"
    adata.write_h5ad(out, compression="gzip")
    print(f"\nwrote {out}  ({out.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
