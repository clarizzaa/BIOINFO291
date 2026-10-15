"""Mechanical checks for a statistical review.

Loaded automatically with the `statistical-review` skill, and re-exported by
`src/statistical_review.py` so workflow scripts do not depend on the skill
harness (the same arrangement as `skills/figure-contract/`).

Each function implements one check from `docs/statistical-review.md` and names
the rule it serves. Nothing here decides anything: these return numbers, and the
reviewer decides what they mean.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

__all__ = [
    "wilcox_test_R", "sign_test", "signrank_floor", "permutation_floor",
    "n_from_statistic", "glm_p_rlike", "collect_family", "correct_family",
    "reconcile_n", "split_pasted_blocks",
]


# --------------------------------------------------------------------------
# Reproducing R (step 4 of the procedure)
# --------------------------------------------------------------------------

def wilcox_test_R(x, y=None):
    """R's ``wilcox.test(x, y, paired=TRUE)``, conventions included.

    R drops zero differences, then uses the exact signed-rank distribution when
    fewer than 50 non-zero differences remain with no ties, and otherwise the
    normal approximation **with** a continuity correction. ``V`` is the sum of
    the ranks of the positive differences, so it depends on argument order:
    ``V(x, y) + V(y, x) == n * (n + 1) / 2``. A paper reporting the complement
    of your value has computed the same test in the other direction (R2).

    Returns ``(V, n, p, method, zeros_dropped)``.
    """
    x = np.asarray(x, dtype=float)
    d = x if y is None else x - np.asarray(y, dtype=float)
    d = d[~np.isnan(d)]
    n_with_zeros = len(d)
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return float("nan"), 0, float("nan"), "undefined", n_with_zeros
    absd = np.abs(d)
    ties = len(np.unique(absd)) != n
    V = float(stats.rankdata(absd)[d > 0].sum())
    exact = n < 50 and not ties and n_with_zeros == n
    p = float(stats.wilcoxon(d, zero_method="wilcox", alternative="two-sided",
                             method="exact" if exact else "approx",
                             correction=not exact).pvalue)
    return V, n, p, ("exact" if exact else "normal+cc"), n_with_zeros - n


def sign_test(d):
    """Exact two-sided sign test on differences (S9).

    The signed-rank null needs differences symmetric about zero; the sign test
    needs only a zero median, so it stays valid when symmetry fails. Run it
    beside a signed-rank claim whose differences are skewed: agreement is what
    licenses the signed-rank reading.

    Returns ``(k_positive, n_nonzero, p, skewness)``.
    """
    d = np.asarray(d, dtype=float)
    d = d[~np.isnan(d)]
    nz = d[d != 0]
    if len(nz) == 0:
        return 0, 0, float("nan"), float("nan")
    k = int((nz > 0).sum())
    return (k, len(nz), float(stats.binomtest(k, len(nz), 0.5).pvalue),
            float(stats.skew(nz)))


def glm_p_rlike(fit, n_obs: int, term: str) -> float:
    """p-value for one coefficient as ``summary.glm`` would print it.

    statsmodels' GLM reports a z-statistic; R's ``summary.glm`` for the gaussian
    family uses t on residual degrees of freedom. R's AIC additionally counts the
    dispersion parameter, so R's value sits 2.000 above a statsmodels fit of the
    same model - a constant offset, not a different model.
    """
    df_resid = n_obs - len(fit.params)
    return float(2 * stats.t.sf(abs(fit.tvalues[term]), df=df_resid))


# --------------------------------------------------------------------------
# Resolution floors (S11)
# --------------------------------------------------------------------------

def signrank_floor(n: int) -> float:
    """Smallest attainable two-sided signed-rank / sign-test p at this n.

    With five non-zero pairs the floor is 2/32 = 0.0625, so "p < 0.05" is
    unattainable however large the effect. Report this beside any p-value from a
    small exact test.
    """
    return float(2 / 2 ** n) if n > 0 else float("nan")


def permutation_floor(n_permutations: int) -> float:
    """Smallest attainable p from ``(k + 1) / (N + 1)`` with k = 0.

    A permutation p-value quoted below this was not obtainable from the number
    of permutations run.
    """
    return 1.0 / (n_permutations + 1)


# --------------------------------------------------------------------------
# Recovering the unit a test counted (S3, S4, S5)
# --------------------------------------------------------------------------

def n_from_statistic(kind: str, **kw):
    """Recover the n a reported statistic implies, to compare with the subjects.

    ``kind`` is one of:

    - ``"wilcoxon_V"``  (``V=``)      -> the smallest n whose support contains V,
      since ``V <= n(n+1)/2``. A V of 7108 needs n >= 119.
    - ``"glm_df"``      (``df_resid=``, ``n_params=``) -> rows fitted.
    - ``"kruskal_groups"`` (``n_per_group=``) -> total rows tested.

    Returns a dict with the implied n and a one-line interpretation. Comparing
    that n with the number of independently assigned subjects is step 3 of the
    procedure, and is where most blocking findings come from.
    """
    if kind == "wilcoxon_V":
        V = float(kw["V"])
        n = int(math.ceil((-1 + math.sqrt(1 + 8 * V)) / 2))
        return {"implied_n_min": n,
                "note": f"V={V:g} requires at least {n} paired observations "
                        f"(V <= n(n+1)/2 = {n * (n + 1) // 2})"}
    if kind == "glm_df":
        n = int(kw["df_resid"]) + int(kw["n_params"])
        return {"implied_n": n,
                "note": f"residual df {kw['df_resid']} with {kw['n_params']} "
                        f"parameters implies {n} rows fitted"}
    if kind == "kruskal_groups":
        g = list(kw["n_per_group"])
        return {"implied_n": int(sum(g)),
                "note": f"groups {g} imply {sum(g)} rows tested"}
    raise ValueError(f"unknown kind {kind!r}; expected wilcoxon_V, glm_df or "
                     "kruskal_groups")


def reconcile_n(paper: dict, deposit: dict) -> list[dict]:
    """Line up every n printed in the paper against a count in the deposit (S4).

    Both arguments map a label to a count. There is no tolerance on a count: a
    disagreement is a finding even when the conclusion is unaffected.
    """
    rows = []
    for label in sorted(set(paper) | set(deposit)):
        p, d = paper.get(label), deposit.get(label)
        rows.append({"quantity": label, "paper_says": p, "deposit_contains": d,
                     "agrees": (p == d) if (p is not None and d is not None)
                               else None})
    return rows


def split_pasted_blocks(df, subject_col: str = "Subject",
                        summary_marker: str = "average"):
    """Separate real rows from interleaved summary rows in a deposited sheet.

    Deposited spreadsheets routinely paste independent blocks side by side and
    interleave rows like ``"Control averages:"`` inside the data region. Those
    rows are the aggregate the paper tested, so they must be found rather than
    silently averaged in with the subjects.

    Returns ``(real_rows, summary_rows)``.
    """
    label = df[subject_col].astype(str)
    is_summary = label.str.contains(summary_marker, case=False, na=False)
    is_blank = label.isin(["nan", "None", ""])
    return df[~is_summary & ~is_blank], df[is_summary]


# --------------------------------------------------------------------------
# The family (S13)
# --------------------------------------------------------------------------

def collect_family(*tables) -> list[dict]:
    """Flatten per-analysis tables into one family of reported tests (S13).

    Each table is an iterable of dicts carrying at least ``test_id``, ``family``
    and ``p``. ``test_id`` must be stable across tables: joining recomputation
    tables on human-readable labels drops rows when a label is written two ways.
    Raises on a duplicate or missing id rather than correcting a family that is
    quietly short.
    """
    out, seen = [], set()
    for table in tables:
        for row in table:
            tid = row.get("test_id")
            if not tid:
                raise ValueError(f"row without test_id: {row}")
            if tid in seen:
                raise ValueError(f"duplicate test_id {tid!r}")
            seen.add(tid)
            out.append(dict(row))
    return out


def correct_family(pvalues, alpha: float = 0.05) -> dict:
    """Bonferroni and Benjamini-Hochberg over one family (S13).

    Both are returned because they answer different questions - Bonferroni
    "could any of these be chance?", BH "what fraction of the called positives
    are chance?" - and neither replaces the other.
    """
    p = np.asarray(list(pvalues), dtype=float)
    n = len(p)
    bonf = np.minimum(p * n, 1.0)
    bh = multipletests(p, method="fdr_bh")[1]
    return {"n_tests": n, "alpha": alpha,
            "bonferroni": bonf, "BH_q": bh,
            "n_sig_raw": int((p < alpha).sum()),
            "n_sig_bonferroni": int((bonf < alpha).sum()),
            "n_sig_BH": int((bh < alpha).sum())}
