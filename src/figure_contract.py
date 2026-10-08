"""Importable entry point for the figure-contract helpers.

The helpers have a single source: `skills/figure-contract/kernel.py`. That
location is fixed by the Claude Science skill format, which executes a file
named `kernel.py` at the skill root when an agent loads the skill. This module
puts the same functions on a normal import path so that workflow scripts do
not depend on the skill harness:

    from src.figure_contract import contract_style, save_figure

Workflows import from here. Agents load the skill. Both get the same code,
and a clean checkout reproduces every figure with no platform involvement.

Relationship to `src/plotting.py`
---------------------------------
`src/plotting.py` is week 1's house style for the melanoma analysis: fixed
entity colours (response groups, cell types), a UMAP embedding helper, and
significance stars. It answers "what should this project's figures look like".

This module answers a different question: "what must a figure declare, and
which rules must it keep". The two are not alternatives and neither wraps the
other -- `plotting.apply_style` and `contract_style` both set rcParams, so a
script should call one or the other, not both.

Week-2 figures go through `save_figure` here, because only this path writes
the sidecar. Week-1 figures predate the contract and are grandfathered in
`figures/PRE_CONTRACT.txt`. Converging the two modules would mean reopening
week-1 workflows, which was deliberately out of scope; see reports/DECISIONS.md.
"""

import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "figure-contract"
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

from kernel import *  # noqa: F401,F403,E402
from kernel import (  # noqa: F401,E402  explicit re-export
    BANNED_COLORMAPS,
    DIVERGING,
    INTERVAL_NAMES,
    OKABE_ITO,
    SEQUENTIAL,
    SIDECAR_AUTO,
    SIDECAR_CONDITIONAL,
    SIDECAR_REQUIRED,
    annotate_n,
    check_palette,
    contract_caption,
    contract_style,
    git_sha,
    interval,
    interval_name,
    is_missing,
    line_with_gaps,
    save_figure,
    strip_with_units,
    trajectories_by_group,
    unit_level,
)
