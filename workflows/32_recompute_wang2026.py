#!/usr/bin/env python
"""Step 32 - recompute every statistic Wang & Horowitz 2026 reports.

Inputs   : configs/statreview.yaml
           data/raw/papers/wang2026-conspecific-odors/Part_1.xlsx, Part_2.xlsx
Outputs  : results/statistical_reviews/wang2026-conspecific-odors/
               n_reconciliation.csv      counts in the deposit vs counts in the paper
               recompute_part1.csv       16 Wilcoxon signed-rank tests
               recompute_part2.csv       8 omnibus tests, at the unit the paper used
               recompute_dunn.csv        11 Dunn post-hoc comparisons
               recompute_glm.csv         4 sex x condition coefficients
               unit_comparison.csv       Part 2 at the time bin vs at the dog
               pvalue_family.csv         all 39 tests as published, corrected
               pvalue_family_at_dog.csv  all 39 with Part 2 re-tested on dogs
Env      : bioinfo291-stats   (environment/env-stats.yml)

Rules exercised: S3/S5 (unit), S4 (n), S9 (rank tests), S11 (p-value floor),
S13 (family). See docs/statistical-review.md.

Every table carries a `test_id` so downstream steps join on a stable key rather
than on a human-readable label.

    python workflows/32_recompute_wang2026.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scikit_posthocs as sp
import statsmodels.api as smapi
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

SLUG = "wang2026-conspecific-odors"
BINS = [f"{i}s" for i in range(5, 65, 5)]
ORDER = ["C", "J", "S"]

# Reported values, transcribed from the Results section of the article PDF.
# Each row: test_id, label, the two columns compared, reported V, reported p.
PART1_POOLED = [
    ("p1.pooled.habituation",    "pooled: habit1 vs habit3",  "habit1", "habit3", 7108.0, 0.001),
    ("p1.pooled.discrimination", "pooled: novel vs habit4",   "habit4", "novel",  2704.0, 0.008),
    ("p1.pooled.dishabituation", "pooled: novel vs habit3",   "habit3", "novel",  2061.5, 0.001),
    ("p1.pooled.format",         "pooled: habit3 vs habit4",  "habit3", "habit4", 2977.0, 0.087),
]
PART1_PAIRINGS = [
    ("p1.JB.discrimination", "JB: novel vs habit4", "JBhabit4", "JBnovel", 226.0, 0.013),
    ("p1.JB.dishabituation", "JB: novel vs habit3", "JBhabit3", "JBnovel", 133.0, 0.001),
    ("p1.SB.discrimination", "SB: novel vs habit4", "SBhabit4", "SBnovel", 412.0, 0.820),
    ("p1.SJ.discrimination", "SJ: novel vs habit4", "SJhabit4", "SJnovel", 301.0, 0.095),
    ("p1.SJ.dishabituation", "SJ: novel vs habit3", "SJhabit3", "SJnovel", 127.0, 0.001),
]
# Order-specific columns. "_vB" means "in a joy-versus-baseline comparison", so
# Jhabit4_vB (joy habituated) pairs with Bnovel_vJ (baseline novel).
PART1_ORDERS = [
    ("p1.JhabBnov.discrim",  "J habituated, B novel: novel vs habit4", "Jhabit4_vB", "Bnovel_vJ", 26.0, 0.004),
    ("p1.BhabJnov.discrim",  "B habituated, J novel: novel vs habit4", "Bhabit4_vJ", "Jnovel_vB", 94.0, 0.470),
    ("p1.JhabBnov.dishab",   "J habituated, B novel: novel vs habit3", "Jhabit3_vB", "Bnovel_vJ", 25.0, 0.003),
    ("p1.BhabJnov.dishab",   "B habituated, J novel: novel vs habit3", "Bhabit3_vJ", "Jnovel_vB", 44.0, 0.042),
    ("p1.ShabJnov.discrim",  "S habituated, J novel: novel vs habit4", "Shabit4_vJ", "Jnovel_vS", 23.0, 0.001),
    ("p1.ShabJnov.dishab",   "S habituated, J novel: novel vs habit3", "Shabit3_vJ", "Jnovel_vS", 29.0, 0.003),
    ("p1.JhabSnov.dishab",   "J habituated, S novel: novel vs habit3", "Jhabit3_vS", "Snovel_vJ", 34.0, 0.045),
]
PART2_OMNIBUS = {               # sheet: (test as stated, reported statistic, reported p)
    "stressbehav": ("Kruskal-Wallis", 20.96,   0.001),
    "joybehav":    ("Kruskal-Wallis", 23.98,   0.001),
    "owner":       ("Kruskal-Wallis", 23.11,   0.001),
    "box":         ("ANOVA",           1.035,  0.370),
    "stranger":    ("Kruskal-Wallis",  8.28,   0.016),
    "upright":     ("Kruskal-Wallis", 16.89,   0.001),
    "sit":         ("Kruskal-Wallis",  5.08,   0.079),
    "prone":       ("Kruskal-Wallis", 15.6326, 0.001),
}
PART2_DUNN = [                  # sheet, group pair, reported p
    ("stressbehav", "C", "J", 0.001), ("stressbehav", "C", "S", 0.001),
    ("joybehav",    "C", "J", 0.001), ("joybehav",    "C", "S", 0.001),
    ("owner",       "C", "S", 0.001), ("owner",       "J", "S", 0.001),
    ("stranger",    "C", "S", 0.002),
    ("upright",     "C", "J", 0.001), ("upright",     "C", "S", 0.004),
    ("prone",       "C", "J", 0.001), ("prone",       "C", "S", 0.005),
]
PART2_GLM = {                   # sheet: (reported AIC, beta, SE, t, p)
    "stressbehav": (-39.927, -0.281, 0.100, -2.796, 0.007),
    "joybehav":    ( 45.290,  0.943, 0.181,  5.201, 0.001),
    "owner":       (-42.484, -0.300, 0.099, -3.044, 0.003),
    "stranger":    (-11.885,  0.339, 0.122,  2.780, 0.007),
}


def wilcox_test_R(x, y):
    """Reproduce R's wilcox.test(x, y, paired=TRUE) default behaviour.

    R drops zero differences, then uses the exact signed-rank distribution when
    fewer than 50 non-zero differences remain with no ties, and otherwise the
    normal approximation with a continuity correction. V is the sum of the
    ranks of the positive differences, so it depends on the order of the
    arguments: V(x, y) + V(y, x) = n(n+1)/2.
    """
    d = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    d = d[~np.isnan(d)]
    n_with_zeros = len(d)
    d = d[d != 0]
    n = len(d)
    zeros = n_with_zeros - n
    absd = np.abs(d)
    ties = len(np.unique(absd)) != n
    V = stats.rankdata(absd)[d > 0].sum()
    exact = n < 50 and not ties and zeros == 0
    p = stats.wilcoxon(d, zero_method="wilcox", alternative="two-sided",
                       method="exact" if exact else "approx",
                       correction=not exact).pvalue
    return V, n, float(p), ("exact" if exact else "normal+cc"), zeros


def signrank_floor(n: int) -> float:
    """S11 - the smallest attainable two-sided signed-rank p-value at this n."""
    return float(2 / 2 ** n) if n > 0 else float("nan")


def part2_blocks(p2: dict, sheet: str):
    """Split one behavioural sheet into its per-dog and per-time-bin blocks.

    The deposited sheets hold three blocks side by side: the raw per-dog record
    with three interleaved "<condition> averages:" rows; the (Condition,
    Frequency) block, which is those average rows turned sideways and is what
    the published tests were run on; and the "_MF" block, the same split by sex.
    """
    raw = p2[sheet]
    subject = raw["Subject"].astype(str)
    dogs = raw[subject.str.startswith("Dog_")]
    values = dogs[BINS].apply(pd.to_numeric, errors="coerce")
    per_dog = pd.DataFrame({
        "dog": dogs["Subject"].to_numpy(),
        "sex": dogs["Sex"].to_numpy() if "Sex" in dogs else np.nan,
        "odor": dogs["Odor"].to_numpy(),
        "value": values.mean(axis=1).to_numpy(),
        "n_bins": values.notna().sum(axis=1).to_numpy(),
    }).dropna(subset=["value"])
    per_bin = raw[["Condition", "Frequency"]].dropna().rename(
        columns={"Condition": "odor", "Frequency": "value"})
    return per_dog, per_bin


def omnibus(groups: list[np.ndarray], test: str) -> tuple[float, float]:
    if test == "ANOVA":
        f, p = stats.f_oneway(*groups)
    else:
        f, p = stats.kruskal(*groups)
    return float(f), float(p)


def main() -> int:
    cfg = load_config("statreview")
    P = paths()
    rtol = cfg["recompute"]["agreement_rtol"]
    out = P.root / cfg["outputs"]["results"] / SLUG
    out.mkdir(parents=True, exist_ok=True)
    deposit = P.root / cfg["outputs"]["raw"] / SLUG
    p1 = pd.read_excel(deposit / "Part_1.xlsx", sheet_name=None)
    p2 = pd.read_excel(deposit / "Part_2.xlsx", sheet_name=None)
    spec, pair, alls = p1["specificorders"], p1["emotionalpairings"], p1["all"]

    # ---- Part 1: 16 Wilcoxon signed-rank tests -----------------------------
    rows = []
    for source, table in ((PART1_POOLED, alls), (PART1_PAIRINGS, pair), (PART1_ORDERS, spec)):
        for test_id, label, hab, nov, V_rep, p_rep in source:
            # The paper's V is the habituated-minus-novel direction for every
            # comparison except the two whose columns are listed in that order
            # already; V(a,b) + V(b,a) = n(n+1)/2, so both are recorded and the
            # direction the paper used is reported rather than assumed (R2).
            V, n, p, method, zeros = wilcox_test_R(table[hab], table[nov])
            V_opposite, _, _, _, _ = wilcox_test_R(table[nov], table[hab])
            rows.append({
                "test_id": test_id, "comparison": label, "n": n,
                "V_reported": V_rep, "V_recomputed": V, "V_opposite_direction": V_opposite,
                "V_matches": bool(abs(V - V_rep) < 0.51),
                "p_reported": p_rep, "p_recomputed": p, "method": method,
                "zeros_dropped": zeros, "p_floor_at_this_n": signrank_floor(n),
            })
    part1 = pd.DataFrame(rows)
    part1.to_csv(out / "recompute_part1.csv", index=False)

    # ---- Part 1 at the dog level (S3) --------------------------------------
    # The pooled tests stack 122 dog x pairing rows from 43 dogs. Averaging each
    # dog's pairings to one value per dog gives the same comparison with the dog
    # as the unit.
    rows = []
    for test_id, label, cols in (
        ("p1.dog.discrimination", "discrimination (novel - habit4), one value per dog",
         ["JBdiscrmdifference", "SBdiscrmdifference", "SJdiscrmdifference"]),
        ("p1.dog.dishabituation", "dishabituation (novel - habit3), one value per dog",
         ["JBdishabitdifference", "SBdishabitdifference", "SJdishabitdifference"]),
    ):
        per_dog = pair[cols].mean(axis=1, skipna=True).dropna()
        V, n, p, method, zeros = wilcox_test_R(per_dog, np.zeros(len(per_dog)))
        pooled_id = ("p1.pooled.discrimination" if "discrim" in test_id
                     else "p1.pooled.dishabituation")
        # S9: the signed-rank null needs differences symmetric about zero. The
        # sign test needs only a zero median, so it stays valid if symmetry
        # fails; agreement between the two is what licenses the signed-rank
        # reading. Skewness is reported rather than tested.
        d = per_dog.to_numpy(dtype=float)
        nz = d[d != 0]
        k_pos = int((nz > 0).sum())
        p_sign = float(stats.binomtest(k_pos, len(nz), 0.5).pvalue)
        skew = float(stats.skew(nz))
        rows.append({
            "test_id": test_id, "comparison": label,
            "n_pooled_rows": len(alls), "n_dogs": n,
            "p_pooled": float(part1.set_index("test_id").loc[pooled_id, "p_recomputed"]),
            "p_per_dog": p, "V_per_dog": V, "method": method,
            "median_per_dog_seconds": round(float(per_dog.median()), 3),
            "mean_per_dog_seconds": round(float(per_dog.mean()), 3),
            "sig_per_dog": bool(p < cfg["review"]["alpha"]),
            "sign_test_k_positive": k_pos, "sign_test_n": len(nz),
            "sign_test_p": p_sign, "difference_skewness": round(skew, 3),
            "sign_test_agrees": bool((p < cfg["review"]["alpha"])
                                     == (p_sign < cfg["review"]["alpha"])),
        })
    pd.DataFrame(rows).to_csv(out / "part1_dog_level.csv", index=False)

    # ---- Part 2: 8 omnibus tests, at the unit the paper used ----------------
    rows, unit_rows = [], []
    for sheet, (test, stat_rep, p_rep) in PART2_OMNIBUS.items():
        per_dog, per_bin = part2_blocks(p2, sheet)
        gb = [per_bin.loc[per_bin.odor == k, "value"].to_numpy(float) for k in ORDER]
        gd = [per_dog.loc[per_dog.odor == k, "value"].to_numpy(float) for k in ORDER]
        s_bin, p_bin = omnibus(gb, test)
        s_dog, p_dog = omnibus(gd, test)
        rows.append({
            "test_id": f"p2.omnibus.{sheet}", "outcome": sheet, "test_as_stated": test,
            "n_per_group": "/".join(str(len(g)) for g in gb),
            "stat_reported": stat_rep, "stat_recomputed": round(s_bin, 4),
            "stat_matches": bool(abs(s_bin - stat_rep) <= max(0.01, rtol * abs(stat_rep))),
            "p_reported": p_rep, "p_recomputed": p_bin,
        })
        unit_rows.append({
            "test_id": f"p2.omnibus.{sheet}", "outcome": sheet,
            "n_bins_per_group": "/".join(str(len(g)) for g in gb), "p_on_bins": p_bin,
            "n_dogs_per_group": "/".join(str(len(g)) for g in gd), "p_on_dogs": p_dog,
            "sig_on_bins": bool(p_bin < cfg["review"]["alpha"]),
            "sig_on_dogs": bool(p_dog < cfg["review"]["alpha"]),
        })
    part2 = pd.DataFrame(rows)
    part2.to_csv(out / "recompute_part2.csv", index=False)
    pd.DataFrame(unit_rows).to_csv(out / "unit_comparison.csv", index=False)

    # ---- Part 2: 11 Dunn post-hoc comparisons ------------------------------
    rows = []
    for sheet, g1, g2, p_rep in PART2_DUNN:
        per_dog, per_bin = part2_blocks(p2, sheet)
        m_bin = sp.posthoc_dunn(per_bin, val_col="value", group_col="odor", p_adjust=None)
        m_dog = sp.posthoc_dunn(per_dog, val_col="value", group_col="odor", p_adjust=None)
        p_bin = float(m_bin.loc[g1, g2])
        rows.append({
            "test_id": f"p2.dunn.{sheet}.{g1}{g2}", "outcome": sheet, "pair": f"{g1} vs {g2}",
            "p_reported": p_rep, "p_on_bins_two_sided": p_bin,
            # R's dunn.test prints a one-tailed p by default; the paper's values
            # match half of the two-sided value (S6, R2).
            "p_on_bins_one_tailed": p_bin / 2,
            "p_on_dogs_two_sided": float(m_dog.loc[g1, g2]),
        })
    dunn = pd.DataFrame(rows)
    dunn.to_csv(out / "recompute_dunn.csv", index=False)

    # ---- Part 2: 4 sex x condition coefficients ----------------------------
    rows = []
    for sheet, (aic_rep, b_rep, se_rep, t_rep, p_rep) in PART2_GLM.items():
        d = p2[sheet][["Condition_MF", "Frequency_MF", "Sex_MF"]].dropna()
        d = d.rename(columns={"Condition_MF": "cond", "Frequency_MF": "freq", "Sex_MF": "sex"})
        m = smf.glm("freq ~ cond * sex", data=d, family=smapi.families.Gaussian()).fit()
        term = min(m.params.index, key=lambda k: abs(m.params[k] - b_rep))
        df_resid = len(d) - len(m.params)
        # R's summary.glm for the gaussian family uses t, not z, on residual df.
        p_bin = float(2 * stats.t.sf(abs(m.tvalues[term]), df=df_resid))

        per_dog, _ = part2_blocks(p2, sheet)
        md = smf.glm("value ~ odor * sex", data=per_dog.dropna(subset=["sex"]),
                     family=smapi.families.Gaussian()).fit()
        inter = [k for k in md.params.index if ":" in k]
        p_dog = min(float(2 * stats.t.sf(abs(md.tvalues[k]),
                                         df=len(per_dog) - len(md.params))) for k in inter)
        rows.append({
            "test_id": f"p2.glm.{sheet}", "outcome": sheet, "term": term,
            "n_rows_used": len(d), "n_dogs": int(per_dog.dog.nunique()),
            "AIC_reported": aic_rep, "AIC_recomputed": round(float(m.aic), 3),
            "beta_reported": b_rep, "beta_recomputed": round(float(m.params[term]), 4),
            "SE_reported": se_rep, "SE_recomputed": round(float(m.bse[term]), 4),
            "t_reported": t_rep, "t_recomputed": round(float(m.tvalues[term]), 4),
            "p_reported": p_rep, "p_recomputed": p_bin, "p_on_dogs": p_dog,
            "beta_matches": bool(abs(m.params[term] - b_rep) < 0.01),
        })
    glm = pd.DataFrame(rows)
    glm.to_csv(out / "recompute_glm.csv", index=False)

    # ---- The family (S13) --------------------------------------------------
    fam = []
    for _, r in part1.iterrows():
        fam.append({"test_id": r.test_id, "family": "Part 1 Wilcoxon", "test": r.comparison,
                    "p_published_unit": r.p_recomputed, "p_dog_unit": r.p_recomputed,
                    "unit_published": "dog x pairing", "unit_defensible": "dog"})
    for _, r in part2.iterrows():
        d = next(u for u in unit_rows if u["test_id"] == r.test_id)
        fam.append({"test_id": r.test_id, "family": "Part 2 omnibus",
                    "test": f"{r.outcome} ({r.test_as_stated})",
                    "p_published_unit": r.p_recomputed, "p_dog_unit": d["p_on_dogs"],
                    "unit_published": "time bin", "unit_defensible": "dog"})
    for _, r in dunn.iterrows():
        fam.append({"test_id": r.test_id, "family": "Part 2 Dunn post-hoc",
                    "test": f"{r.outcome} {r.pair}",
                    "p_published_unit": r.p_on_bins_two_sided, "p_dog_unit": r.p_on_dogs_two_sided,
                    "unit_published": "time bin", "unit_defensible": "dog"})
    for _, r in glm.iterrows():
        fam.append({"test_id": r.test_id, "family": "Part 2 sex x condition GLM",
                    "test": f"{r.outcome}: {r.term}",
                    "p_published_unit": r.p_recomputed, "p_dog_unit": r.p_on_dogs,
                    "unit_published": "time bin", "unit_defensible": "dog"})
    F = pd.DataFrame(fam)
    alpha = cfg["review"]["alpha"]
    for col, tag in (("p_published_unit", ""), ("p_dog_unit", "_at_dog")):
        F[f"bonferroni{tag}"] = np.minimum(F[col] * len(F), 1.0)
        F[f"BH_q{tag}"] = multipletests(F[col], method="fdr_bh")[1]
        F[f"sig_raw{tag}"] = F[col] < alpha
        F[f"sig_BH{tag}"] = F[f"BH_q{tag}"] < alpha
    F.to_csv(out / "pvalue_family.csv", index=False)
    F.to_csv(out / "pvalue_family_at_dog.csv", index=False)

    # ---- n reconciliation (S4) ---------------------------------------------
    seasons = sorted(spec["Season"].astype(str).value_counts().to_list())
    per_dog_owner, per_bin_owner = part2_blocks(p2, "owner")
    nrec = pd.DataFrame([
        ("dogs recruited", "43", str(spec["Subject"].nunique()), "yes", ""),
        ("data-collection periods", "14 / 17 / 12", " / ".join(map(str, seasons)), "yes",
         "sorted; file labels them 2025-04-24, 2025-11-24, Feb-Mar24"),
        ("Part 1 joy-baseline pairings", "40", str(int(pair["JBnovel"].notna().sum())), "yes",
         "pairings, not dogs"),
        ("Part 1 stress-baseline pairings", "41", str(int(pair["SBnovel"].notna().sum())), "yes",
         "pairings, not dogs"),
        ("Part 1 stress-joy pairings", "41", str(int(pair["SJnovel"].notna().sum())), "yes",
         "pairings, not dogs"),
        ("Part 1 pooled test input", "not stated", f"{len(alls)} paired rows", "n/a",
         "40+41+41 pairings contributed by 43 dogs"),
        ("Part 2 dogs analyzed (blank/joy/stress)", "6 / 9 / 9",
         " / ".join(str(int((per_dog_owner.odor == k).sum())) for k in ORDER), "yes",
         "24 total, between-subjects"),
        ("Part 2 omnibus test input", "not stated",
         f"{len(per_bin_owner)} rows ({int((per_bin_owner.odor == 'C').sum())} per condition)",
         "n/a", "time-bin means; the 24 dogs are averaged away"),
        ("Part 2 GLM input", "not stated",
         f"{len(p2['owner'][['Condition_MF', 'Frequency_MF', 'Sex_MF']].dropna())} rows", "n/a",
         "12 bins x 3 conditions x 2 sexes"),
    ], columns=["quantity", "paper says", "deposit contains", "agrees", "note"])
    nrec.to_csv(out / "n_reconciliation.csv", index=False)

    print(f"Part 1: {int(part1.V_matches.sum())}/{len(part1)} V statistics reproduce")
    print(f"Part 2: {int(part2.stat_matches.sum())}/{len(part2)} omnibus statistics reproduce")
    print(f"GLM:    {int(glm.beta_matches.sum())}/{len(glm)} coefficients reproduce")
    print(f"family: {len(F)} reported tests; "
          f"significant raw {int(F.sig_raw.sum())}, BH {int(F.sig_BH.sum())}; "
          f"at the dog level BH {int(F.sig_BH_at_dog.sum())}")
    print(f"wrote 9 tables to {out.relative_to(P.root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
