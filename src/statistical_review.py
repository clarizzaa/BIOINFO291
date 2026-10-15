"""Importable entry point for the statistical-review helpers.

The helpers have a single source: `skills/statistical-review/kernel.py`. That
location is fixed by the Claude Science skill format, which executes a file
named `kernel.py` at the skill root when an agent loads the skill. This module
puts the same functions on a normal import path so that workflow scripts do not
depend on the skill harness:

    from statistical_review import wilcox_test_R, correct_family

Workflows import from here. Agents load the skill. Both get the same code, and a
clean checkout reproduces every review number with no platform involvement.

This mirrors `src/figure_contract.py`, which does the same for the figure rules.
The two are independent: a statistical review cites `S` rules from
`docs/statistical-review.md` for the inference and `C` rules from
`docs/figure-contract.md` for the drawing, and the review's own figures go
through `save_figure` from the other module.

Note on import order: `skills/statistical-review/` is prepended to `sys.path`
below, and both skill directories contain a module named `kernel`. Import this
module and `figure_contract` in either order - each inserts its own directory at
position 0 and binds its own names before the other can shadow it - but do not
`import kernel` directly in a workflow script, because which one you get depends
on which skill module was imported last.
"""

import sys
from pathlib import Path

_SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "statistical-review"
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

# Imported by file path rather than by bare module name, because
# skills/figure-contract/ also ships a module called `kernel`.
import importlib.util as _ilu  # noqa: E402

_spec = _ilu.spec_from_file_location("_statreview_kernel", _SKILL_DIR / "kernel.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

collect_family = _mod.collect_family
correct_family = _mod.correct_family
glm_p_rlike = _mod.glm_p_rlike
n_from_statistic = _mod.n_from_statistic
permutation_floor = _mod.permutation_floor
reconcile_n = _mod.reconcile_n
sign_test = _mod.sign_test
signrank_floor = _mod.signrank_floor
split_pasted_blocks = _mod.split_pasted_blocks
wilcox_test_R = _mod.wilcox_test_R

__all__ = [
    "collect_family", "correct_family", "glm_p_rlike", "n_from_statistic",
    "permutation_floor", "reconcile_n", "sign_test", "signrank_floor",
    "split_pasted_blocks", "wilcox_test_R",
]
