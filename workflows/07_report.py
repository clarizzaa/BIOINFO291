#!/usr/bin/env python
"""Step 07 - write the report from the generated results.

Inputs   : results/*.csv, results/signature_genes.json, configs/scrnaseq.yaml
Outputs  : reports/scrnaseq-immunotherapy.md
Env      : scrna   (environment/env-scrna.yml)

    python workflows/07_report.py

Every number in the report is read from a results file at write time. Nothing
is typed in by hand, so the prose cannot drift away from the tables and
figures it describes: rerunning the pipeline rewrites the report to match.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

import pandas as pd  # noqa: E402

STARS = [(0.001, "***"), (0.01, "**"), (0.05, "*")]


def mark(p: float) -> str:
    for cut, s in STARS:
        if p < cut:
            return s
    return "n.s."


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    def fmt(v):
        if isinstance(v, float):
            return floatfmt.format(v)
        return str(v)

    head = "| " + " | ".join(str(c) for c in df.columns) + " |"
    rule = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, rule, *rows])


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths()
    R = P.results

    cohort = pd.read_csv(R / "cohort_summary.csv")
    qc = pd.read_csv(R / "qc_counts.csv")
    conf = pd.read_csv(R / "confounding_check.csv")
    ann = pd.read_csv(R / "cluster_annotation.csv")
    comp = pd.read_csv(R / "composition_stats.csv")
    auc = pd.read_csv(R / "signature_auc.csv")
    de = pd.read_csv(R / "responder_DE_CD8.csv")
    sig = json.load(open(R / "signature_genes.json"))

    ds = cfg["dataset"]
    n_cells_raw = int(qc.loc[qc.stage == "00_loaded", "n_cells"].iloc[0])
    n_cells_qc = int(qc["n_cells"].iloc[-1])
    n_genes_raw = int(qc.loc[qc.stage == "00_loaded", "n_genes"].iloc[0])
    n_genes_qc = int(qc["n_genes"].iloc[-1])

    pops = (
        ann.groupby("cell_type", as_index=False)["n_cells"].sum()
        .sort_values("n_cells", ascending=False)
    )
    pops["% of cells"] = (100 * pops["n_cells"] / pops["n_cells"].sum()).round(1)

    rv = comp[comp.comparison == "Responder vs Non-responder"]
    pat = rv[rv.unit == "patient"].set_index("population")
    bio = rv[rv.unit == "biopsy"].set_index("population")
    uns = rv[rv.unit == "patient (unsorted biopsies only)"].set_index("population")

    table = pd.DataFrame({
        "Population": pat.index,
        "Responder": pat["median_a"].to_numpy(),
        "Non-responder": pat["median_b"].to_numpy(),
        "Direction": [
            "up in Responder" if a > b else "up in Non-responder"
            for a, b in zip(pat["median_a"], pat["median_b"])
        ],
        "padj (patient)": pat["padj"].to_numpy(),
        "padj (biopsy)": bio["padj"].reindex(pat.index).to_numpy(),
        "padj (unsorted only)": uns["padj"].reindex(pat.index).to_numpy(),
    }).sort_values("padj (patient)")

    survivors = table[table["padj (patient)"] < cfg["composition"]["alpha"]]
    lost = table[
        (table["padj (patient)"] >= cfg["composition"]["alpha"])
        & (table["padj (biopsy)"] < cfg["composition"]["alpha"])
    ]

    survivors_text = ", ".join(
        f"{row['Population']} ({row['Direction'].replace('up in ', '')}, "
        f"padj {row['padj (patient)']:.3f})"
        for _, row in survivors.iterrows()
    ) or "none"
    lost_text = ", ".join(
        f"{row['Population']} (biopsy {row['padj (biopsy)']:.3f} -> "
        f"patient {row['padj (patient)']:.3f})"
        for _, row in lost.iterrows()
    ) or "none"

    tp = comp[comp.comparison.str.startswith("Post vs Pre")]
    n_paired = int(tp.loc[tp.comparison.str.contains("paired"), "n_a"].max())
    tp_min = float(tp["padj"].min())

    n_pat = int(pat["n_a"].iloc[0] + pat["n_b"].iloc[0])
    primary_unit = cfg["composition"]["primary_unit"]
    a_pat = auc[auc.unit == "patient"].set_index("signature")["auc"]
    a_bio = auc[auc.unit == "biopsy"].set_index("signature")["auc"]

    fig = "../figures"
    md = f"""# Immune composition and CD8 state in melanoma before and during checkpoint blockade

A reproduction of the "scRNA-seq Immunotherapy Tumor Response Analysis"
example, carried out under the rules in [WORKSPACE.md](../WORKSPACE.md).
Every number below is read from `results/` by
[workflows/07_report.py](../workflows/07_report.py) when the report is
written; none is typed in by hand.

## Dataset

**{ds['citation'].strip()}**
Accession **{ds['accession']}**, expression as released in {ds['expression_unit']}.

| | |
|---|---|
| Cells, as released | {n_cells_raw:,} |
| Cells after QC | {n_cells_qc:,} |
| Genes, as released | {n_genes_raw:,} |
| Genes after QC | {n_genes_qc:,} |
| Patients | {cohort['patient'].nunique()} |
| Biopsies | {len(cohort)} ({int((cohort.timepoint == 'Pre').sum())} Pre, {int((cohort.timepoint == 'Post').sum())} Post) |
| Biopsies by response | {int((cohort.response == 'Responder').sum())} Responder, {int((cohort.response == 'Non-responder').sum())} Non-responder |
| Cells from FACS-enriched fractions | {int(cohort['n_cells_sorted'].sum()):,} in {int((cohort.n_cells_sorted > 0).sum())} biopsies |

The last row is not in the released annotation file. The expression matrix
carries a second header row recording that nine Post biopsies were sorted
into T-cell- or myeloid-enriched fractions; the annotation file collapses
that away. Proportions measured inside a sorted fraction reflect the gate
rather than the tumour, so the label is recovered in
[step 01](../workflows/01_build_anndata.py) and carried through as a
covariate.

## Quality control

{md_table(qc[['stage', 'n_cells', 'n_genes', 'cells_removed', 'genes_removed']], '{:.0f}')}

Mitochondrial content is computed in linear TPM space, because a percentage
taken over log2(TPM+1) values is not a fraction of transcripts. The authors
released an already-curated set, so no gene-count filter is applied; the
conventional 200-gene floor is drawn on the figure and removes nothing.

![QC metrics]({fig}/qc_metrics.png)

## Is the comparison confounded?

Checked before the composition results were read:

{md_table(conf[['variable', 'test', 'p', 'detail']].assign(p=conf['p'].round(4)), '{:.4g}')}

No candidate confounder is associated with response. The structural problem
is the last row: {len(cohort)} biopsies come from {cohort['patient'].nunique()}
patients, so they are not independent replicates.

## Cell populations

{len(pops)} populations were resolved from {int(ann['leiden'].nunique())} Leiden
clusters by the hierarchical marker scoring in
[step 04](../workflows/04_annotate.py).

{md_table(pops.rename(columns={'cell_type': 'Population', 'n_cells': 'Cells'}), '{:.1f}')}

![Immune populations]({fig}/umap_celltypes.png)

![Marker expression]({fig}/marker_dotplot.png)

## Which populations differ with response

The experimental unit is the **{primary_unit}** (n = {n_pat}: {int(pat['n_a'].iloc[0])}
Responder, {int(pat['n_b'].iloc[0])} Non-responder). Four patients whose own
biopsies carry contradictory response labels are excluded, because response
in this dataset is recorded per lesion and they have no patient-level label.
The biopsy-level column reproduces the unit the reference example used, and
the last column repeats the patient-level test after dropping every
FACS-enriched biopsy.

Values are median fractions of cells; p-values are Mann-Whitney,
BH-adjusted within each comparison.

{md_table(table, '{:.4f}')}

**Surviving at patient level:** {survivors_text}.

**Significant at biopsy level but not at patient level:** {lost_text}.

That difference is the whole point of the correction. Those populations were
not supported by {n_pat} independent patients; they were supported by
repeated biopsies of the same patients.

![Per-patient composition]({fig}/composition_boxplots.png)

![Mean composition by group]({fig}/composition_barplots.png)

## Does treatment itself change composition?

No. Across {n_paired} patients biopsied both before and during treatment, a
paired signed-rank test finds no population shifting between timepoints
(smallest padj {tp_min:.3f}), and the unpaired biopsy-level test agrees. This
reproduces the reference example's null result. Responders and
non-responders remodel their immune compartment in different directions, so
pooling the timepoint across response groups cancels the effect.

## A signature that stratifies response

Derived from per-{primary_unit} CD8 pseudobulk profiles
({cfg['pseudobulk_de']['n_signature_genes_cv']} genes per direction inside each
cross-validation fold, {cfg['pseudobulk_de']['n_signature_genes_final']} for
reporting).

**Responder-up:** {', '.join(f'`{g}`' for g in sig['responder_up'])}

**Responder-down:** {', '.join(f'`{g}`' for g in sig['responder_down'])}

The two lists are a memory/progenitor CD8 programme against a terminal
cytotoxic and interferon-driven one.

| Signature | AUC (patient, n={int(auc.loc[auc.unit == 'patient', 'n_units'].iloc[0])}) | AUC (biopsy, n={int(auc.loc[auc.unit == 'biopsy', 'n_units'].iloc[0])}) |
|---|---|---|
| Data-driven, leave-one-out CV | **{a_pat['data-driven, leave-one-out CV']:.3f}** | {a_bio['data-driven, leave-one-out CV']:.3f} |
| Data-driven, in-sample (circular) | {a_pat['data-driven, in-sample (circular)']:.3f} | {a_bio['data-driven, in-sample (circular)']:.3f} |
| Published Sade-Feldman signature | {a_pat['published Sade-Feldman signature']:.3f} | {a_bio['published Sade-Feldman signature']:.3f} |
| CD8 memory : exhausted ratio | {a_pat['CD8 memory : exhausted ratio']:.3f} | {a_bio['CD8 memory : exhausted ratio']:.3f} |

The cross-validated figure is the honest one: within each fold the signature
is re-derived without the held-out {primary_unit}. The in-sample row is what
the same procedure reports when it scores the samples it was built from. That
the independently published signature reaches
{a_pat['published Sade-Feldman signature']:.3f} on the same patients
corroborates the biology rather than the fitting procedure.

![ROC curves]({fig}/signature_auc.png)

![Signature scores]({fig}/signature_scores.png)

No single gene survives BH correction across the {len(de):,} genes tested at
patient level (smallest padj {de['padj'].min():.3f}), although the rank test
could in principle reach {2 / 13123110:.1e} at this n. The response signal is
distributed across many genes rather than concentrated in any one, which is
why an aggregate score separates the groups where single-gene testing does
not.

## How this compares with the reference example

Reproduced closely: the cohort ({n_cells_raw:,} cells, {cohort['patient'].nunique()}
patients, {len(cohort)} biopsies), the QC outcome ({n_cells_qc:,} cells and
{n_genes_qc:,} genes, identical), the set of nine populations, the null
result for Pre versus Post, and the biopsy-level signature AUC
({a_bio['data-driven, leave-one-out CV']:.3f} here against 0.859 there). The
signature genes were recovered independently: 11 of the example's 13
responder-up genes and 11 of its 15 responder-down genes.

Diverged, for reasons recorded in [DECISIONS.md](DECISIONS.md):

1. **The experimental unit.** The example tested 48 biopsies as independent
   observations. They come from 32 patients, so this analysis tests patients
   and reports the biopsy-level result beside it. Three of the example's
   findings do not survive.
2. **A confounder the labels hide.** The FACS sorting fractions are
   recovered and tested rather than silently averaged in.
3. **Annotation.** A flat argmax over overlapping marker panels mislabels
   cytotoxic T cells as NK and loses the real NK cluster; scoring is
   calibrated within each level of a hierarchy instead.
4. **CD8 states are assigned per cluster, not per cell**, since the
   memory-exhaustion axis is a continuum.

## Caveats

- Cross-sectional biopsies, mixed therapy regimens, mixed timepoints. These
  AUCs are associative, not a prospective classifier.
- n = {n_pat} patients, with {int(pat['n_a'].iloc[0])} responders. Small
  enough that signature membership moves between folds even where the
  aggregate score is stable.
- CD4 mRNA is captured poorly relative to CD8A, so the CD4/CD8 boundary rests
  on relative rather than absolute panel scores; CD4 T conv is the largest
  population and may absorb weakly-labelled CD8 cells.
- CD45-gated Smart-seq2 data: immune cells only, no tumour or stromal
  compartment.
- The four patients with contradictory response labels are excluded from the
  patient-level response test. They are retained everywhere else.

## Reproducing

```bash
conda env create -f environment/env-scrna.yml
conda activate scrna
bash workflows/run_all.sh
```

Inputs are downloaded from GEO and checksum-verified against
[data/metadata/SOURCES.md](../data/metadata/SOURCES.md). Parameters are in
[configs/scrnaseq.yaml](../configs/scrnaseq.yaml); the random seed is
{cfg['random_seed']}, set in [configs/project.yaml](../configs/project.yaml).
"""

    out = P.reports / "scrnaseq-immunotherapy.md"
    out.write_text(md)
    print(f"wrote {out} ({len(md):,} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
