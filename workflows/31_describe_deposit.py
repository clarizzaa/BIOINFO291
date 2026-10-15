#!/usr/bin/env python
"""Step 31 - describe a paper's data deposit before any statistic is computed.

Inputs   : configs/statreview.yaml
           data/raw/papers/<slug>/   (placed by workflows/30_fetch_papers.py)
Outputs  : results/statistical_reviews/<slug>/deposit_inventory.csv
           stdout: every sheet, its shape, its columns, and its first rows
Env      : bioinfo291-stats   (environment/env-stats.yml)

A review cannot cite a column it has not looked at. This step is deliberately
dumb: it opens everything in the deposit and shows what is there, so the
reported n in the paper can be checked against a real table rather than
assumed (docs/statistical-review.md S4, R4).

    python workflows/31_describe_deposit.py <slug>
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

HEAD_ROWS = 5
MAX_COLS_SHOWN = 14


def describe_excel(path: Path) -> list[dict]:
    """Print every sheet in a workbook and return one inventory row per sheet."""
    book = pd.read_excel(path, sheet_name=None)
    rows = []
    for sheet, df in book.items():
        print(f"\n  ── sheet {sheet!r}: {df.shape[0]} rows x {df.shape[1]} columns")
        cols = list(df.columns)
        shown = cols[:MAX_COLS_SHOWN]
        print(f"     columns: {shown}")
        if len(cols) > MAX_COLS_SHOWN:
            print(f"              ... and {len(cols) - MAX_COLS_SHOWN} more")
        with pd.option_context("display.width", 200, "display.max_columns", MAX_COLS_SHOWN):
            print(df.head(HEAD_ROWS).to_string(max_cols=MAX_COLS_SHOWN))
        rows.append({
            "file": path.name,
            "sheet": sheet,
            "n_rows": df.shape[0],
            "n_cols": df.shape[1],
            "columns": "; ".join(str(c) for c in cols),
        })
    return rows


def describe_text(path: Path, n_lines: int = 40) -> list[dict]:
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    print(f"\n  ── {path.name}: {len(lines)} lines, {len(text)} characters")
    for ln in lines[:n_lines]:
        print(f"     {ln}")
    if len(lines) > n_lines:
        print(f"     ... and {len(lines) - n_lines} more lines")
    return [{"file": path.name, "sheet": "", "n_rows": len(lines), "n_cols": "",
             "columns": ""}]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    slug = argv[1]
    cfg = load_config("statreview")
    P = paths()
    deposit = P.root / cfg["outputs"]["raw"] / slug
    if not deposit.is_dir():
        print(f"no deposit at {deposit}; run workflows/30_fetch_papers.py first")
        return 1

    print(f"deposit: {deposit.relative_to(P.root)}")
    inventory: list[dict] = []
    for path in sorted(deposit.iterdir()):
        if path.name == "paper.pdf":
            print(f"\n  ── {path.name}: {path.stat().st_size / 1e6:.1f} MB (the article)")
            continue
        print(f"\n{path.name}  ({path.stat().st_size / 1e3:.1f} kB)")
        if path.suffix.lower() in {".xlsx", ".xls"}:
            inventory += describe_excel(path)
        elif path.suffix.lower() in {".csv", ".tsv"}:
            sep = "\t" if path.suffix.lower() == ".tsv" else ","
            df = pd.read_csv(path, sep=sep)
            print(f"  {df.shape[0]} rows x {df.shape[1]} columns")
            print(df.head(HEAD_ROWS).to_string(max_cols=MAX_COLS_SHOWN))
            inventory.append({"file": path.name, "sheet": "", "n_rows": df.shape[0],
                              "n_cols": df.shape[1],
                              "columns": "; ".join(map(str, df.columns))})
        else:
            inventory += describe_text(path)

    out_dir = P.root / cfg["outputs"]["results"] / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "deposit_inventory.csv"
    pd.DataFrame(inventory).to_csv(out, index=False)
    print(f"\nwrote {out.relative_to(P.root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
