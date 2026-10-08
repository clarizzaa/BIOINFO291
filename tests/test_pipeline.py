"""Checks on the repository's own rules, not on the biology.

These tests enforce what WORKSPACE.md promises: parameters live in configs,
every workflow step declares its inputs and outputs, every raw file is
registered with a checksum, and the result files have the columns the report
reads. They are deliberately cheap - none of them rerun the analysis.

    conda activate scrna && pytest -q
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import load_config, paths  # noqa: E402

WORKFLOWS = sorted((ROOT / "workflows").glob("[0-9][0-9]_*.py"))


def test_workflows_exist():
    assert len(WORKFLOWS) >= 7, f"expected the numbered pipeline, found {WORKFLOWS}"


def test_config_loads_and_carries_the_seed():
    cfg = load_config("scrnaseq")
    assert cfg["random_seed"] == yaml.safe_load(
        (ROOT / "configs" / "project.yaml").read_text()
    )["random_seed"]
    for section in ("dataset", "qc", "cluster", "annotation", "composition", "pseudobulk_de"):
        assert section in cfg, f"configs/scrnaseq.yaml is missing the '{section}' section"


@pytest.mark.parametrize("step", WORKFLOWS, ids=lambda p: p.name)
def test_step_declares_inputs_and_outputs(step: Path):
    """WORKSPACE.md rule 5: each step states what it reads and writes."""
    head = step.read_text()[:2000]
    assert "Inputs" in head and "Outputs" in head, f"{step.name} has no I/O header"
    assert "Env" in head, f"{step.name} does not name the conda environment it runs in"


@pytest.mark.parametrize("step", WORKFLOWS, ids=lambda p: p.name)
def test_no_hardcoded_thresholds(step: Path):
    """WORKSPACE.md rule 3: thresholds come from the config, not from code.

    Flags numeric keyword arguments to the analysis calls that carry real
    parameters. Figure geometry (figsize, dpi, lw, fontsize) is presentation,
    not a scientific parameter, and is not policed here.
    """
    source = step.read_text()
    banned = re.compile(
        r"\b(n_top_genes|n_comps|n_neighbors|resolution|max_value|min_cells|min_genes|"
        r"n_pcs|random_state|seed)\s*=\s*\d+(?!\s*\])"
    )
    offenders = [
        m.group(0) for m in banned.finditer(source)
        if "cfg[" not in source[max(0, m.start() - 90):m.start()]
    ]
    assert not offenders, f"{step.name} hardcodes {offenders}; move them to configs/"


def test_every_raw_file_is_registered():
    """WORKSPACE.md rule 2: nothing in data/raw without a checksum entry."""
    P = paths()
    registered = (P.metadata / "SOURCES.md").read_text()
    # Scaffolding (README, .gitkeep) is not data and needs no provenance row.
    present = [
        f for f in P.raw.glob("*")
        if f.is_file() and f.name != "README.md" and not f.name.startswith(".")
    ]
    if not present:
        pytest.skip("data/raw is empty; run workflows/00_download_data.py first")
    for f in present:
        assert f.name in registered, f"{f.name} is not registered in SOURCES.md"
        assert re.search(rf"{re.escape(f.name)}.*`[0-9a-f]{{64}}`", registered), \
            f"{f.name} has no SHA-256 in SOURCES.md"


def test_raw_data_is_read_only():
    P = paths()
    files = [f for f in P.raw.glob("*.gz")]
    if not files:
        pytest.skip("data/raw is empty; run workflows/00_download_data.py first")
    for f in files:
        assert not (f.stat().st_mode & 0o200), f"{f.name} is writable; raw data must not be"


EXPECTED_COLUMNS = {
    "qc_counts.csv": {"stage", "n_cells", "n_genes", "cells_removed", "genes_removed"},
    "cohort_summary.csv": {"biopsy", "patient", "timepoint", "response", "therapy", "n_cells"},
    "confounding_check.csv": {"variable", "test", "p", "detail"},
    "composition_stats.csv": {"comparison", "unit", "population", "n_a", "n_b", "p", "padj"},
    "cluster_annotation.csv": {"leiden", "cell_type", "n_cells"},
    "responder_DE_CD8.csv": {"gene", "diff_R_minus_NR", "p", "padj"},
    "signature_auc.csv": {"unit", "signature", "n_units", "auc"},
}


@pytest.mark.parametrize("name,cols", sorted(EXPECTED_COLUMNS.items()))
def test_result_tables_have_expected_columns(name: str, cols: set[str]):
    path = paths().results / name
    if not path.exists():
        pytest.skip(f"{name} not generated yet; run workflows/run_all.sh")
    assert cols <= set(pd.read_csv(path).columns), \
        f"{name} is missing {cols - set(pd.read_csv(path).columns)}"


def test_statistics_report_unit_and_n():
    """WORKSPACE.md section 3: a p-value is never reported without unit and n."""
    path = paths().results / "composition_stats.csv"
    if not path.exists():
        pytest.skip("composition_stats.csv not generated yet")
    df = pd.read_csv(path)
    assert df["unit"].notna().all(), "a p-value is reported without its unit of analysis"
    assert (df["n_a"] > 0).all() and (df["n_b"] > 0).all(), "a p-value is reported without n"
    assert {"patient", "biopsy"} <= set(df["unit"]), \
        "both the patient-level and biopsy-level comparisons must be reported"


def test_patient_level_is_the_primary_unit():
    cfg = load_config("scrnaseq")
    assert cfg["composition"]["primary_unit"] == "patient", \
        "WORKSPACE.md requires the patient as the experimental unit"
