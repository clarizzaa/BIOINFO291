"""Configuration and path resolution shared by every workflow step.

Workflow scripts must not contain thresholds or absolute paths. They call
``load_config()`` and ``paths()`` from here, so a reader can see every
parameter by opening ``configs/`` and never has to read code to find a number.

Usage inside a workflow step::

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
    from config import load_config, paths, set_seed

    cfg = load_config("scrnaseq")
    P = paths()
    adata = sc.read_h5ad(P.processed / "sadefeldman.h5ad")
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path

import yaml


def repo_root() -> Path:
    """Repository root, found by walking up to the directory holding WORKSPACE.md."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "WORKSPACE.md").exists():
            return parent
    raise RuntimeError(f"no WORKSPACE.md above {here}; is this a BIOINFO291 checkout?")


@dataclass(frozen=True)
class Paths:
    root: Path
    raw: Path
    metadata: Path
    processed: Path
    results: Path
    figures: Path
    reports: Path
    configs: Path

    def ensure(self) -> "Paths":
        """Create the writable output directories. Never touches data/raw."""
        for d in (self.processed, self.results, self.figures):
            d.mkdir(parents=True, exist_ok=True)
        return self


def paths() -> Paths:
    """Canonical project paths, read from configs/project.yaml."""
    root = repo_root()
    with open(root / "configs" / "project.yaml") as fh:
        project = yaml.safe_load(fh)
    p = project["paths"]
    return Paths(
        root=root,
        raw=root / p["raw"],
        metadata=root / p["metadata"],
        processed=root / p["processed"],
        results=root / p["results"],
        figures=root / p["figures"],
        reports=root / "reports",
        configs=root / "configs",
    )


def load_config(name: str = "scrnaseq") -> dict:
    """Load ``configs/<name>.yaml`` merged with the project-wide settings.

    The project seed is exposed as ``cfg["random_seed"]`` so a step never has
    to open two files to be reproducible.
    """
    root = repo_root()
    with open(root / "configs" / "project.yaml") as fh:
        project = yaml.safe_load(fh)
    cfg: dict = {}
    path = root / "configs" / f"{name}.yaml"
    if path.exists():
        with open(path) as fh:
            cfg = yaml.safe_load(fh) or {}
    cfg["random_seed"] = project["random_seed"]
    cfg["project"] = project["project"]
    return cfg


def set_seed(seed: int) -> int:
    """Seed every RNG a workflow step can reach, and return the seed used.

    Called at the top of every stochastic step. The value comes from
    configs/project.yaml; no step may pass a literal.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:  # pragma: no cover - numpy is always present in env-scrna
        pass
    return seed
