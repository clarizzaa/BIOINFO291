#!/usr/bin/env python
"""Step 01 - assemble the GSE120575 matrix and clinical labels into an AnnData.

Inputs   : data/raw/GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz
           data/raw/GSE120575_patient_ID_single_cells.txt.gz
           configs/scrnaseq.yaml
Outputs  : data/processed/sadefeldman_raw.h5ad
           results/cohort_summary.csv
Env      : scrna   (environment/env-scrna.yml)

    python workflows/01_build_anndata.py

Three properties of the released files are handled explicitly, because getting
any of them wrong corrupts the analysis silently rather than loudly:

1. The expression file carries TWO header lines: line 1 is the cell barcode,
   line 2 repeats the biopsy of origin for each cell. Line 2 is not data.
2. Every gene row ends with a trailing tab, so data rows parse to one more
   field than the header. The final empty column is dropped by `usecols`.
3. The annotation file is a GEO submission template: the real table starts at
   the "Sample name" header and is followed by protocol boilerplate. Only rows
   whose first field matches "Sample <n>" are cells.

The biopsy label has the form "<timepoint>_<patient>" (e.g. "Pre_P1"), which
is the only place patient identity and timepoint are recorded.
"""

from __future__ import annotations

import gzip
import re
import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

ANNOT_HEADER_MARKER = "Sample name"
ANNOT_ENCODING = "latin-1"
CELL_ROW = re.compile(r"^Sample \d+$")


def read_annotation(path: Path) -> pd.DataFrame:
    """Parse the GEO template into one row per cell."""
    # The protocol boilerplate contains Latin-1 bytes (e.g. the micro sign in
    # reagent volumes), so the file is not valid UTF-8.
    with gzip.open(path, "rt", encoding=ANNOT_ENCODING) as fh:
        lines = fh.read().splitlines()
    header_i = next(i for i, ln in enumerate(lines) if ln.split("\t")[0] == ANNOT_HEADER_MARKER)

    raw = pd.read_csv(
        path, sep="\t", skiprows=header_i, header=0, dtype=str,
        compression="gzip", encoding=ANNOT_ENCODING,
    )
    raw.columns = [c.strip() for c in raw.columns]
    keep = raw[raw["Sample name"].astype(str).str.match(CELL_ROW, na=False)].copy()

    biopsy_col = next(c for c in keep.columns if c.startswith("characteristics: patinet ID"))
    resp_col = next(c for c in keep.columns if c.startswith("characteristics: response"))
    ther_col = next(c for c in keep.columns if c.startswith("characteristics: therapy"))

    obs = pd.DataFrame(
        {
            "biopsy": keep[biopsy_col].str.strip().values,
            "response": keep[resp_col].str.strip().values,
            "therapy": keep[ther_col].str.strip().values,
        },
        index=pd.Index(keep["title"].str.strip().values, name="cell"),
    )
    obs["timepoint"] = obs["biopsy"].str.split("_").str[0]
    obs["patient"] = obs["biopsy"].str.split("_").str[1]
    return obs


def read_expression(path: Path, chunk_rows: int) -> tuple[sp.csr_matrix, list[str], list[str], list[str]]:
    """Stream the genes x cells matrix into a sparse CSR block.

    Returns (matrix, gene_names, cell_names, per-cell biopsy labels from line 2).
    """
    with gzip.open(path, "rt") as fh:
        cells = fh.readline().rstrip("\n").split("\t")[1:]
        biopsy_header = fh.readline().rstrip("\n").split("\t")[1:]
    n_cells = len(cells)
    biopsy_header = biopsy_header[:n_cells]
    print(f"  header declares {n_cells} cells")

    blocks: list[sp.csr_matrix] = []
    genes: list[str] = []
    reader = pd.read_csv(
        path,
        sep="\t",
        skiprows=2,
        header=None,
        usecols=range(n_cells + 1),  # drop the trailing empty field
        chunksize=chunk_rows,
        compression="gzip",
        na_filter=False,
    )
    for i, chunk in enumerate(reader):
        genes.extend(chunk.iloc[:, 0].astype(str).tolist())
        values = chunk.iloc[:, 1:].to_numpy(dtype=np.float32, copy=False)
        blocks.append(sp.csr_matrix(values))
        if (i + 1) % 5 == 0:
            print(f"    parsed {len(genes):,} genes", flush=True)

    X = sp.vstack(blocks, format="csr")
    del blocks
    print(f"  parsed {X.shape[0]:,} genes x {X.shape[1]:,} cells, "
          f"{X.nnz / (X.shape[0] * X.shape[1]):.1%} non-zero")
    return X, genes, cells, biopsy_header


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths().ensure()
    ds, build = cfg["dataset"], cfg["build"]

    print("reading annotation")
    obs = read_annotation(P.raw / ds["files"]["annotation"])
    print(f"  {len(obs):,} annotated cells")

    print("reading expression matrix (streamed)")
    X, genes, cells, biopsy_header = read_expression(
        P.raw / ds["files"]["expression"], build["chunk_rows"]
    )

    # Align annotation to matrix column order, and verify the two independent
    # records of each cell's biopsy agree before trusting any label.
    missing = set(cells) - set(obs.index)
    if missing:
        raise SystemExit(f"{len(missing)} matrix cells absent from the annotation file")
    obs = obs.loc[cells]

    # The matrix header carries information the annotation file drops: nine
    # Post biopsies were FACS-sorted into T-cell- or myeloid-enriched
    # fractions, recorded as a suffix on the biopsy label. Cell-type
    # proportions in a sorted fraction reflect the gate, not the tumour, so
    # this is kept as a covariate and checked for confounding in step 05.
    suffix = [h[len(b):].lstrip("_") for h, b in zip(biopsy_header, obs["biopsy"].to_numpy())]
    bad = [h for h, b in zip(biopsy_header, obs["biopsy"].to_numpy()) if not h.startswith(b)]
    if bad:
        raise SystemExit(
            f"{len(bad)} cells disagree between the matrix header and the annotation file "
            f"beyond a sorting suffix, e.g. {bad[:3]}"
        )
    obs["sort_fraction"] = [s or "unsorted" for s in suffix]
    n_sorted = int((obs["sort_fraction"] != "unsorted").sum())
    print(f"  biopsy labels agree for all {len(obs):,} cells")
    print(f"  {n_sorted:,} cells come from a FACS-enriched fraction "
          f"({sorted(set(obs['sort_fraction']) - {'unsorted'})})")

    adata = ad.AnnData(X=X.T.tocsr(), obs=obs, var=pd.DataFrame(index=pd.Index(genes, name="gene")))
    del X
    adata.var_names_make_unique()
    for col in ("biopsy", "response", "therapy", "timepoint", "patient", "sort_fraction"):
        adata.obs[col] = adata.obs[col].astype("category")
    adata.uns["dataset"] = {
        "accession": ds["accession"],
        "expression_unit": ds["expression_unit"],
        "citation": ds["citation"],
    }

    # Fail loudly if the cohort does not match the published description.
    got = {
        "n_cells": adata.n_obs,
        "n_patients": adata.obs["patient"].nunique(),
        "n_samples": adata.obs["biopsy"].nunique(),
    }
    for key, expected in build["expect"].items():
        if got[key] != expected:
            raise SystemExit(f"cohort check failed: {key} is {got[key]}, expected {expected}")
    print(f"  cohort check passed: {got}")

    # Per-biopsy cohort table: the unit the statistics will later run on.
    cohort = (
        adata.obs.groupby("biopsy", observed=True)
        .agg(
            patient=("patient", "first"),
            timepoint=("timepoint", "first"),
            response=("response", "first"),
            therapy=("therapy", "first"),
            n_cells=("patient", "size"),
            n_cells_sorted=("sort_fraction", lambda s: int((s != "unsorted").sum())),
            sort_fractions=("sort_fraction", lambda s: "+".join(sorted(set(s)))),
        )
        .sort_values(["patient", "timepoint"])
    )
    cohort.to_csv(P.results / "cohort_summary.csv")

    out = P.processed / "sadefeldman_raw.h5ad"
    adata.write_h5ad(out, compression="gzip")
    print(f"\nwrote {out}  ({out.stat().st_size / 1e6:.0f} MB)")
    print(f"wrote {P.results / 'cohort_summary.csv'}")
    print(f"\n{adata.n_obs:,} cells x {adata.n_vars:,} genes")
    print(cohort.groupby(["timepoint", "response"], observed=True).size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
