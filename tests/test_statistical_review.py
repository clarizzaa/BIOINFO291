"""Checks on the statistical-review contract (docs/statistical-review.md).

Run:  pytest -q   from the repository root, in the bioinfo291-stats environment.

Three kinds of check:
  1. the helpers reproduce the conventions they claim to reproduce, against
     values taken from lecture 3 and from the reviewed paper;
  2. every review directory carries its record, and every review figure its
     sidecar;
  3. the review's own numbers agree with the tables the workflow wrote, so a
     REVIEW.md cannot drift away from its evidence.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from statistical_review import (  # noqa: E402
    collect_family, correct_family, n_from_statistic, sign_test, signrank_floor,
    split_pasted_blocks, wilcox_test_R,
)

REVIEWS = REPO / "reports" / "statistical_reviews"
RESULTS = REPO / "results" / "statistical_reviews"


# ---------------------------------------------------------------- helpers

def test_signrank_floor_matches_lecture_3():
    """Slide 25: five non-zero pairs cannot produce a two-sided p below 0.0625."""
    assert signrank_floor(5) == pytest.approx(0.0625)
    assert signrank_floor(6) == pytest.approx(0.03125)


def test_wilcoxon_V_directions_are_complementary():
    """V(x, y) + V(y, x) == n(n+1)/2, which is why a paper can report either."""
    rng = np.random.default_rng(0)
    x, y = rng.normal(size=40), rng.normal(size=40)
    v1, n, _, _, _ = wilcox_test_R(x, y)
    v2, _, _, _, _ = wilcox_test_R(y, x)
    assert v1 + v2 == pytest.approx(n * (n + 1) / 2)


def test_wilcoxon_switches_to_the_exact_distribution_below_50():
    rng = np.random.default_rng(1)
    _, _, _, method_small, _ = wilcox_test_R(rng.normal(size=20) + 0.5)
    _, _, _, method_large, _ = wilcox_test_R(rng.normal(size=60) + 0.5)
    assert method_small == "exact"
    assert method_large == "normal+cc"


def test_wilcoxon_drops_zero_differences_as_R_does():
    d = np.array([1.0, 2.0, 0.0, 0.0, -3.0])
    _, n, _, _, zeros = wilcox_test_R(d)
    assert (n, zeros) == (3, 2)


def test_n_from_statistic_recovers_the_unit_a_statistic_implies():
    """V = 7108 cannot come from 43 dogs; it needs at least 119 paired rows."""
    out = n_from_statistic("wilcoxon_V", V=7108)
    assert out["implied_n_min"] == 119
    assert n_from_statistic("glm_df", df_resid=66, n_params=6)["implied_n"] == 72


def test_sign_test_needs_no_symmetry():
    """Nine +1s and one -20: positive signs dominate while the mean is negative."""
    k, n, p, _ = sign_test(np.array([1.0] * 9 + [-20.0]))
    assert (k, n) == (9, 10)
    assert p == pytest.approx(0.021484375)


def test_collect_family_refuses_a_quietly_short_family():
    rows = [{"test_id": "a", "family": "f", "p": 0.01}]
    with pytest.raises(ValueError):
        collect_family(rows, rows)                       # duplicate id
    with pytest.raises(ValueError):
        collect_family([{"family": "f", "p": 0.01}])      # missing id


def test_correct_family_reports_both_corrections():
    out = correct_family([0.001, 0.04, 0.2])
    assert out["n_tests"] == 3
    assert out["n_sig_raw"] == 2
    assert out["n_sig_bonferroni"] == 1


def test_split_pasted_blocks_finds_interleaved_summary_rows():
    df = pd.DataFrame({"Subject": ["Dog_1", "Dog_2", "Control averages:", "Dog_3"],
                       "v": [1, 2, 1.5, 3]})
    real, summary = split_pasted_blocks(df)
    assert len(real) == 3 and len(summary) == 1


# ------------------------------------------------------- the review record

def review_dirs():
    return [d for d in sorted(REVIEWS.iterdir()) if d.is_dir()] if REVIEWS.is_dir() else []


@pytest.mark.parametrize("d", review_dirs(), ids=lambda d: d.name)
def test_every_review_has_its_record(d):
    assert (d / "REVIEW.md").is_file(), f"{d.name} has no REVIEW.md"
    assert (d / "review.json").is_file(), f"{d.name} has no review.json"
    rec = json.loads((d / "review.json").read_text())
    for field in ("paper", "verdict", "claims"):
        assert field in rec, f"{d.name}/review.json is missing {field!r}"
    assert rec["verdict"] in {"ship", "revise", "blocked", "not_reviewable"}
    for claim in rec["claims"]:
        assert claim["verdict"] in {"supported", "weakened", "unsupported"}
        for f in claim["findings"]:
            assert f["severity"] in {"blocking", "major", "minor"}
            assert f["rule"], "every finding cites a rule identifier"


@pytest.mark.parametrize("d", review_dirs(), ids=lambda d: d.name)
def test_the_paper_verdict_follows_from_its_claims(d):
    rec = json.loads((d / "review.json").read_text())
    verdicts = {c["verdict"] for c in rec["claims"]}
    expected = ("blocked" if "unsupported" in verdicts
                else "revise" if "weakened" in verdicts else "ship")
    if rec["verdict"] != "not_reviewable":
        assert rec["verdict"] == expected, (
            f"{d.name}: claims are {sorted(verdicts)} so the paper verdict should be "
            f"{expected!r}, not {rec['verdict']!r}")


@pytest.mark.parametrize("d", review_dirs(), ids=lambda d: d.name)
def test_every_review_figure_has_a_sidecar(d):
    for png in sorted((d / "figures").glob("*.png")) if (d / "figures").is_dir() else []:
        sidecar = png.with_suffix("").with_suffix(".contract.json")
        assert sidecar.is_file(), f"{png.relative_to(REPO)} has no sidecar"
        rec = json.loads(sidecar.read_text())
        script = REPO / rec["source_script"]
        assert script.is_file(), (
            f"{sidecar.name} declares source_script {rec['source_script']!r}, "
            "which does not exist")


# ------------------------------------------------- the review's own numbers

WANG = "wang2026-conspecific-odors"


@pytest.mark.skipif(not (RESULTS / WANG / "pvalue_family.csv").is_file(),
                    reason="run workflows/32_recompute_wang2026.py first")
def test_wang2026_family_is_complete_and_its_counts_match_the_review():
    fam = pd.read_csv(RESULTS / WANG / "pvalue_family.csv")
    rec = json.loads((REVIEWS / WANG / "review.json").read_text())
    assert len(fam) == rec["summary"]["family_size_reported"] == 39
    # The four sub-families the Results report: 16 + 8 + 11 + 4.
    assert fam.family.value_counts().to_dict() == {
        "Part 1 Wilcoxon": 16, "Part 2 Dunn post-hoc": 11,
        "Part 2 omnibus": 8, "Part 2 sex x condition GLM": 4}
    part2 = fam[fam.family.str.startswith("Part 2")]
    assert int(part2.sig_BH_at_dog.sum()) == rec["summary"]["part2_significant_after_reanalysis"]


@pytest.mark.skipif(not (RESULTS / WANG / "recompute_part1.csv").is_file(),
                    reason="run workflows/32_recompute_wang2026.py first")
def test_wang2026_reported_statistics_all_reproduce():
    p1 = pd.read_csv(RESULTS / WANG / "recompute_part1.csv")
    p2 = pd.read_csv(RESULTS / WANG / "recompute_part2.csv")
    glm = pd.read_csv(RESULTS / WANG / "recompute_glm.csv")
    assert p1.V_matches.all(), "a Part 1 V statistic no longer reproduces"
    assert p2.stat_matches.all(), "a Part 2 omnibus statistic no longer reproduces"
    assert glm.beta_matches.all(), "a GLM coefficient no longer reproduces"
