#!/usr/bin/env python
"""Step 06 - pseudobulk differential expression and a responder signature.

Inputs   : data/processed/sadefeldman_annotated.h5ad
           configs/scrnaseq.yaml  (pseudobulk_de.*, benchmark_signature.*)
Outputs  : results/responder_DE_CD8.csv
           results/responder_DE_all.csv
           results/signature_genes.json
           results/signature_auc.csv
           figures/signature_auc.png
           figures/signature_scores.png
Env      : scrna   (environment/env-scrna.yml)

    python workflows/06_pseudobulk_de.py

Cells are aggregated to one profile per unit before testing. Testing genes
across 16,060 individual cells would treat cells from one patient as
independent replicates and return p-values inflated by orders of magnitude;
the aggregation is what makes the test answer the question actually asked,
which is about patients.

The signature AUC is cross-validated. Picking the most different genes on all
samples and then scoring those same samples measures how well a rule fits the
data it was built from, not how well it would stratify a new patient. Both
numbers are reported so the gap between them is visible, and an independently
published signature is scored on the same units as an external benchmark.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths, prepare_runtime, set_seed  # noqa: E402

prepare_runtime()  # must precede the scanpy import

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import scanpy as sc  # noqa: E402
import scipy.sparse as sp  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.metrics import roc_auc_score, roc_curve  # noqa: E402
from statsmodels.stats.multitest import multipletests  # noqa: E402

from plotting import GREY, RESPONSE_COLORS, apply_style, save, strip_with_median  # noqa: E402


def pseudobulk(adata, unit_key: str) -> tuple[pd.DataFrame, pd.Series]:
    """Mean log2(TPM+1) per unit (units x genes), plus cells contributing."""
    labels = adata.obs[unit_key].astype(str).to_numpy()
    units = pd.Index(sorted(set(labels)), name=unit_key)
    pos = {u: i for i, u in enumerate(units)}
    rows = np.fromiter((pos[v] for v in labels), dtype=np.int32, count=len(labels))
    ind = sp.csr_matrix(
        (np.ones(len(labels), dtype=np.float32), (rows, np.arange(len(labels)))),
        shape=(len(units), adata.n_obs),
    )
    n_cells = np.asarray(ind.sum(axis=1)).ravel()
    summed = ind @ adata.X
    mat = np.asarray(summed.todense() if sp.issparse(summed) else summed, dtype=np.float32)
    mat /= n_cells[:, None]
    return (pd.DataFrame(mat, index=units, columns=adata.var_names.to_numpy()),
            pd.Series(n_cells.astype(int), index=units, name="n_cells"))


def de_table(pb: pd.DataFrame, response: pd.Series, method: str) -> pd.DataFrame:
    """Per-gene Mann-Whitney between responder and non-responder units."""
    r = pb.loc[response[response == "Responder"].index].to_numpy()
    nr = pb.loc[response[response == "Non-responder"].index].to_numpy()
    expressed = (r.mean(axis=0) > 0) | (nr.mean(axis=0) > 0)
    genes = pb.columns.to_numpy()[expressed]
    r, nr = r[:, expressed], nr[:, expressed]
    # Vectorised over genes; scipy handles the tie correction per column.
    u, p = stats.mannwhitneyu(r, nr, axis=0)
    out = pd.DataFrame({
        "gene": genes,
        "mean_responder": r.mean(axis=0).round(4),
        "mean_non_responder": nr.mean(axis=0).round(4),
        "diff_R_minus_NR": (r.mean(axis=0) - nr.mean(axis=0)).round(4),
        "statistic": u, "p": p,
    })
    out["padj"] = multipletests(out["p"], method=method)[1]
    return out.sort_values("p").reset_index(drop=True)


def pick_signature(pb: pd.DataFrame, response: pd.Series, cfg_de: dict,
                   n_genes: int, drop: re.Pattern) -> tuple[list[str], list[str]]:
    """Top up- and down-genes by mean difference, after expression and noise filters."""
    r = pb.loc[response[response == "Responder"].index].mean()
    nr = pb.loc[response[response == "Non-responder"].index].mean()
    eligible = (r > cfg_de["min_group_mean"]) | (nr > cfg_de["min_group_mean"])
    diff = (r - nr)[eligible]
    diff = diff[[not drop.match(g) for g in diff.index]]
    ranked = diff.sort_values(ascending=False)
    return ranked.index[:n_genes].tolist(), ranked.index[-n_genes:][::-1].tolist()


def score_units(pb: pd.DataFrame, up: list[str], down: list[str]) -> np.ndarray:
    """Signature score: mean expression of the up set minus the down set."""
    u = [g for g in up if g in pb.columns]
    d = [g for g in down if g in pb.columns]
    return (pb[u].mean(axis=1) - pb[d].mean(axis=1)).to_numpy()


def loo_scores(pb: pd.DataFrame, response: pd.Series, cfg_de: dict,
               drop: re.Pattern) -> np.ndarray:
    """Leave-one-out scores: the signature is re-derived without the held-out unit."""
    units = list(pb.index)
    out = np.zeros(len(units))
    for i, held in enumerate(units):
        train = [u for u in units if u != held]
        up, down = pick_signature(pb.loc[train], response.loc[train], cfg_de,
                                  cfg_de["n_signature_genes_cv"], drop)
        out[i] = score_units(pb.loc[[held]], up, down)[0]
    return out


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths().ensure()
    seed = set_seed(cfg["random_seed"])
    de_cfg, bench = cfg["pseudobulk_de"], cfg["benchmark_signature"]
    apply_style()
    drop = re.compile(de_cfg["exclude_gene_pattern"])

    adata = sc.read_h5ad(P.processed / "sadefeldman_annotated.h5ad")
    cd8 = adata[adata.obs["cell_type"].isin(de_cfg["compartment_populations"])].copy()
    print(f"loaded {adata.n_obs:,} cells; CD8 compartment = {cd8.n_obs:,} cells")

    # Patients whose biopsies disagree about response have no patient-level
    # label, exactly as in step 05.
    label_by_patient = adata.obs.groupby("patient", observed=True)["response"].agg(
        lambda s: s.iloc[0] if s.nunique() == 1 else "Inconsistent"
    )
    consistent = label_by_patient[label_by_patient != "Inconsistent"]

    frames: dict[str, tuple[pd.DataFrame, pd.Series]] = {}
    for unit in (de_cfg["primary_unit"], de_cfg["secondary_unit"]):
        pb, n = pseudobulk(cd8, unit)
        keep = n >= de_cfg["min_cd8_cells_per_sample"]
        if unit == "patient":
            keep &= pb.index.isin(consistent.index)
        pb = pb[keep]
        resp = (
            consistent.reindex(pb.index) if unit == "patient"
            else adata.obs.groupby(unit, observed=True)["response"].first().reindex(pb.index)
        ).astype(str)
        frames[unit] = (pb, resp)
        print(f"  {unit}-level CD8 pseudobulk: {len(pb)} units "
              f"({(resp == 'Responder').sum()} R / {(resp == 'Non-responder').sum()} NR), "
              f"{int(n[keep].min())} cells minimum")

    # --- differential expression -------------------------------------------
    pb_p, resp_p = frames[de_cfg["primary_unit"]]
    de_cd8 = de_table(pb_p, resp_p, de_cfg["multiple_testing"])
    de_cd8.to_csv(P.results / "responder_DE_CD8.csv", index=False)
    print(f"  wrote {P.results / 'responder_DE_CD8.csv'} "
          f"({(de_cd8.padj < 0.05).sum()} genes at padj<0.05, "
          f"{(de_cd8.p < 0.05).sum()} at unadjusted p<0.05)")

    pb_all, n_all = pseudobulk(adata, de_cfg["primary_unit"])
    keep_all = (n_all >= de_cfg["min_cells_per_sample_all"]) & pb_all.index.isin(consistent.index)
    de_all = de_table(pb_all[keep_all], consistent.reindex(pb_all[keep_all].index).astype(str),
                      de_cfg["multiple_testing"])
    de_all.to_csv(P.results / "responder_DE_all.csv", index=False)
    print(f"  wrote {P.results / 'responder_DE_all.csv'} "
          f"({(de_all.padj < 0.05).sum()} genes at padj<0.05)")

    # --- signatures and their honest performance ----------------------------
    auc_rows, curves, score_frames = [], {}, {}
    final_up, final_down = pick_signature(
        pb_p, resp_p, de_cfg, de_cfg["n_signature_genes_final"], drop
    )
    print(f"\nresponder-UP ({len(final_up)}): {', '.join(final_up)}")
    print(f"responder-DOWN ({len(final_down)}): {', '.join(final_down)}")

    for unit, (pb, resp) in frames.items():
        y = (resp == "Responder").astype(int).to_numpy()
        cv = loo_scores(pb, resp, de_cfg, drop)
        up, down = pick_signature(pb, resp, de_cfg, de_cfg["n_signature_genes_cv"], drop)
        insample = score_units(pb, up, down)
        paper = score_units(pb, bench["responder"], bench["non_responder"])
        ratio = _mem_exh_ratio(adata, pb.index, unit, cfg)

        for name, s in (("data-driven, leave-one-out CV", cv),
                        ("data-driven, in-sample (circular)", insample),
                        ("published Sade-Feldman signature", paper),
                        ("CD8 memory : exhausted ratio", ratio)):
            ok = np.isfinite(s)
            auc_rows.append({"unit": unit, "signature": name, "n_units": int(ok.sum()),
                             "n_responder": int(y[ok].sum()),
                             "auc": round(float(roc_auc_score(y[ok], s[ok])), 3)})
            curves[(unit, name)] = roc_curve(y[ok], s[ok])
        score_frames[unit] = pd.DataFrame({"response": resp.to_numpy(), "cv": cv,
                                           "paper": paper}, index=pb.index)

    auc = pd.DataFrame(auc_rows)
    auc.to_csv(P.results / "signature_auc.csv", index=False)
    print(f"\n{auc.to_string(index=False)}")

    json.dump(
        {"responder_up": final_up, "responder_down": final_down,
         "benchmark_responder": bench["responder"],
         "benchmark_non_responder": bench["non_responder"],
         "unit": de_cfg["primary_unit"],
         "auc": auc.to_dict(orient="records")},
        open(P.results / "signature_genes.json", "w"), indent=2,
    )
    print(f"  wrote {P.results / 'signature_genes.json'}")

    # --- figures ------------------------------------------------------------
    palette = {"data-driven, leave-one-out CV": "#1f6fb4",
               "data-driven, in-sample (circular)": "#9fc4e4",
               "published Sade-Feldman signature": "#d98e04",
               "CD8 memory : exhausted ratio": GREY}
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.9))
    for ax, unit in zip(axes, frames):
        for name, color in palette.items():
            fpr, tpr, _ = curves[(unit, name)]
            a = auc.loc[(auc.unit == unit) & (auc.signature == name), "auc"].iloc[0]
            ax.plot(fpr, tpr, color=color, lw=1.8,
                    ls="--" if "circular" in name else "-",
                    label=f"{name} ({a:.2f})")
        ax.plot([0, 1], [0, 1], color="#cccccc", lw=1, zorder=0)
        n = int(auc.loc[auc.unit == unit, "n_units"].iloc[0])
        ax.set_xlabel("false positive rate")
        ax.set_title(f"{unit.capitalize()} level (n={n})")
        ax.set_aspect("equal")
        ax.margins(0.02)
    axes[0].set_ylabel("true positive rate")
    axes[0].legend(loc="lower right", fontsize=6.5)
    # Title quotes the measured drop rather than characterising its size.
    sel = auc[auc.unit == de_cfg["primary_unit"]].set_index("signature")["auc"]
    fig.suptitle(
        f"Cross-validation lowers the data-driven AUC from "
        f"{sel['data-driven, in-sample (circular)']:.2f} to "
        f"{sel['data-driven, leave-one-out CV']:.2f}; the published signature reaches "
        f"{sel['published Sade-Feldman signature']:.2f}",
        x=0.01, ha="left", y=1.02,
    )
    fig.tight_layout()
    save(fig, P.figures / "signature_auc.png", dpi=cfg["figures"]["dpi"])

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.2))
    for ax, (col, label) in zip(axes, [("cv", "data-driven (LOO-CV)"),
                                       ("paper", "published signature")]):
        sf = score_frames[de_cfg["primary_unit"]]
        strip_with_median(ax, {g: sf.loc[sf.response == g, col].to_numpy()
                               for g in ("Responder", "Non-responder")},
                          RESPONSE_COLORS, seed=seed)
        a = auc.loc[(auc.unit == de_cfg["primary_unit"])
                    & (auc.signature.str.contains("leave-one-out" if col == "cv" else "published")),
                    "auc"].iloc[0]
        ax.set_title(f"{label}\nAUC {a:.2f}")
        ax.set_ylabel("signature score" if col == "cv" else "")
    fig.suptitle(f"Per-{de_cfg['primary_unit']} CD8 signature scores",
                 x=0.01, ha="left", y=1.03)
    fig.tight_layout()
    save(fig, P.figures / "signature_scores.png", dpi=cfg["figures"]["dpi"])
    return 0


def _mem_exh_ratio(adata, units, unit_key: str, cfg: dict) -> np.ndarray:
    """CD8 memory-to-exhausted ratio per unit, as a single-feature benchmark."""
    num, den = cfg["composition"]["ratio_numerator"], cfg["composition"]["ratio_denominator"]
    counts = (
        adata.obs.groupby([unit_key, "cell_type"], observed=True).size()
        .unstack(fill_value=0).reindex(index=units, fill_value=0)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        return (counts.get(num, 0) / counts.get(den, 0).replace(0, np.nan)).to_numpy()


if __name__ == "__main__":
    raise SystemExit(main())
