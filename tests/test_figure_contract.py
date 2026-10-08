"""Checks on the figure contract itself (docs/figure-contract.md).

Run:  pytest -q   from the repository root, in the bioinfo291-viz environment.

Two kinds of check:
  1. the helpers enforce the rules they claim to enforce;
  2. every figure in figures/ has a complete sidecar.

The second is the repository-level guard: a figure can reach `figures/` only
through `save_figure`, which refuses an incomplete declaration, but the test
catches a file added by any other route.
"""

import json
import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.figure_contract import (  # noqa: E402
    SIDECAR_AUTO,
    SIDECAR_REQUIRED,
    check_palette,
    interval,
    interval_name,
    line_with_gaps,
    save_figure,
    unit_level,
)

COMPLETE = {
    "question": "q",
    "claim": "c",
    "experimental_unit": "chick",
    "n_per_group": {"1": 16},
    "n_observations": "none; every point is one chick",
    "error_bar": "mean with 95% CI",
    "transformations": [],
    "axes": {},
    "color": {},
    "excluded": "none",
    "missing": "none",
    "source_script": "s.py",
    "config": "c.yaml",
}


def _single_panel():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    return fig


# --- the helpers enforce their rules -------------------------------------

@pytest.mark.parametrize("field", SIDECAR_REQUIRED)
def test_save_figure_refuses_incomplete_sidecar(tmp_path, field):
    """Every required field is actually required (C8, C11, and the sidecar)."""
    contract = {k: v for k, v in COMPLETE.items() if k != field}
    with pytest.raises(ValueError, match="incomplete"):
        save_figure(_single_panel(), tmp_path / "f.png", contract, repo=REPO)


def test_save_figure_requires_shared_scales_declaration(tmp_path):
    """C2 - a multi-panel figure must say whether its panels share scales."""
    fig, _ = plt.subplots(1, 2)
    with pytest.raises(ValueError, match="shared_scales"):
        save_figure(fig, tmp_path / "f.png", COMPLETE, repo=REPO)


def test_save_figure_writes_png_and_sidecar(tmp_path):
    png, sidecar = save_figure(_single_panel(), tmp_path / "f.png", COMPLETE, repo=REPO)
    assert png.exists() and sidecar.exists()
    written = json.loads(sidecar.read_text())
    for field in (*SIDECAR_REQUIRED, *SIDECAR_AUTO):
        assert field in written, field


def test_rainbow_colormaps_are_refused():
    """C6 - rainbow scales invent boundaries in a smooth field."""
    for bad in ("jet", "turbo", "rainbow", "turbo_r"):
        with pytest.raises(ValueError, match="rainbow"):
            check_palette(bad)
    assert check_palette("viridis") == "viridis"


def test_interval_label_states_its_definition():
    """C10 - an interval never comes back without the words that define it."""
    values = [1.0, 2.0, 3.0, 4.0]
    for kind, expected in (("SD", "SD"), ("SE", "SE"), ("CI95", "95% CI")):
        _, half, label = interval(values, kind=kind)
        assert expected in label and "n = 4" in label
        assert half > 0
    # SD > SE for the same data: the three are not interchangeable.
    assert interval(values, "SD")[1] > interval(values, "SE")[1]


def test_interval_name_carries_no_n():
    """C10 - a multi-group figure must not label itself with one group's n."""
    assert "n =" not in interval_name("CI95")


def test_unit_level_collapses_to_one_row_per_unit():
    """C7 - repeated measurements of one unit are not replicates."""
    pd = pytest.importorskip("pandas")
    df = pd.read_csv(REPO / "data" / "raw" / "chickweight.csv")
    final = unit_level(df, unit="chick", group="diet", value="weight",
                       how="last", time="time")
    assert len(final) == df["chick"].nunique()
    assert final["chick"].is_unique


def test_line_with_gaps_preserves_missing():
    """C4 - a hidden mark is not an absent observation."""
    import numpy as np

    fig, ax = plt.subplots()
    (line,) = line_with_gaps(ax, [0, 1, 2], [1.0, None, 3.0])
    assert np.isnan(line.get_ydata()).sum() == 1


# --- repository-level guard ----------------------------------------------

def _pre_contract_figures():
    """Figures explicitly grandfathered in figures/PRE_CONTRACT.txt.

    A named list rather than a date cutoff: an exemption has to be added
    deliberately, in a commit, and is visible to any reader of the repository.
    """
    listing = REPO / "figures" / "PRE_CONTRACT.txt"
    if not listing.exists():
        return set()
    return {
        line.strip()
        for line in listing.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_every_figure_has_a_complete_sidecar():
    """No figure may exist in this repository without declaring itself."""
    exempt = _pre_contract_figures()
    # rglob, not glob: figures are organised into per-dataset subdirectories
    # (figures/chickweight/ and so on), and a non-recursive glob would quietly
    # stop checking every figure the moment one was filed away.
    figures = [p for p in sorted((REPO / "figures").rglob("*.png"))
               if p.name not in exempt]
    assert figures, "no figures found to check; has the figures/ layout changed?"
    for png in figures:
        sidecar = png.with_suffix(".contract.json")
        assert sidecar.exists(), f"{png.name} has no sidecar"
        declared = json.loads(sidecar.read_text())
        absent = [f for f in (*SIDECAR_REQUIRED, *SIDECAR_AUTO)
                  if f not in declared]
        assert not absent, f"{png.name} sidecar missing: {absent}"
        assert declared["figure"] == png.name
        assert declared["n_per_group"], f"{png.name} declares no n"
