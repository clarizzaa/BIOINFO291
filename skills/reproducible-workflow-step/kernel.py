"""Helpers for adding a numbered step to a reproducible-science repository.

Loaded automatically when the `reproducible-workflow-step` skill is loaded.
See SKILL.md for the procedure these support.
"""

import datetime
import pathlib
import re
import string

BANNED_PARAMS = r"\b(n_top_genes|n_comps|n_neighbors|resolution|max_value|min_cells|min_genes|n_pcs|random_state|seed)\s*=\s*\d+"

STEP_TEMPLATE = '''#!/usr/bin/env python
"""Step ${number} - ${purpose}

Inputs   : ${inputs}
Outputs  : ${outputs}
Env      : ${env}

    python workflows/${number}_${slug}.py

${notes}
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths, prepare_runtime, set_seed  # noqa: E402

prepare_runtime()  # must precede any scanpy import

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from plotting import apply_style, save  # noqa: E402


def main() -> int:
    cfg = load_config("${config}")
    P = paths().ensure()
    seed = set_seed(cfg["random_seed"])
    apply_style()

    # Read inputs from disk. Never rely on state left by another step.

    # Record counts before and after every filter into results/.

    # Write outputs. Print computed values, not narration.
    print(f"seed {seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def step_template():
    """Return the raw step skeleton, with ${...} placeholders unfilled."""
    return STEP_TEMPLATE


def scaffold_step(repo, number, slug, purpose, inputs, outputs,
                  env="scrna", config="scrnaseq", notes=""):
    """Write workflows/<number>_<slug>.py from the template. Refuses to clobber.

    `inputs` and `outputs` may be a string or a list of paths; they become the
    declared interface in the docstring header (contract rule 1).
    """
    if isinstance(inputs, (list, tuple)):
        inputs = "\n           ".join(inputs)
    if isinstance(outputs, (list, tuple)):
        outputs = "\n           ".join(outputs)
    if not notes:
        notes = ("Explain here anything a reader would otherwise have to "
                 "reverse-engineer from the code.")
    body = string.Template(STEP_TEMPLATE).substitute(
        number=str(number).zfill(2), slug=slug, purpose=purpose,
        inputs=inputs, outputs=outputs, env=env, config=config, notes=notes,
    )
    dest = pathlib.Path(repo) / "workflows" / (str(number).zfill(2) + "_" + slug + ".py")
    if dest.exists():
        raise FileExistsError(str(dest) + " exists; edit it rather than scaffolding a variant")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body)
    return str(dest)


def wrap_field(text, indent):
    """Wrap a decision-log field to the log's column width."""
    out, line = [], ""
    for word in str(text).split():
        if len(line) + len(word) + 1 > 74 - indent:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    out.append(line)
    return ("\n" + " " * indent).join(out)


def decision_entry(title, decision, alternatives, reason, affects, date=None):
    """Return a DECISIONS.md entry. Append it in the commit that implements it."""
    if date is None:
        date = datetime.date.today().isoformat()
    return (
        "## " + date + "  " + title + "\n"
        "Decision:     " + wrap_field(decision, 14) + "\n"
        "Alternatives: " + wrap_field(alternatives, 14) + "\n"
        "Reason:       " + wrap_field(reason, 14) + "\n"
        "Affects:      " + wrap_field(affects, 14) + "\n"
    )


def audit_steps(repo):
    """Check every numbered step against contract rules 1 and 2.

    Returns {step_name: [problems]} for steps that fail; empty dict if clean.
    """
    banned = re.compile(BANNED_PARAMS)
    findings = {}
    for step in sorted((pathlib.Path(repo) / "workflows").glob("[0-9][0-9]_*.py")):
        source = step.read_text()
        head = source[:2000]
        problems = []
        for field in ("Inputs", "Outputs", "Env"):
            if field not in head:
                problems.append("docstring header does not declare " + field)
        hits = [
            m.group(0) for m in banned.finditer(source)
            if "cfg[" not in source[max(0, m.start() - 90):m.start()]
        ]
        if hits:
            problems.append("hardcoded parameters: " + str(sorted(set(hits))))
        if problems:
            findings[step.name] = problems
    return findings
