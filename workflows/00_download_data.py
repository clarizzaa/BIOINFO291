#!/usr/bin/env python
"""Step 00 - obtain the GSE120575 raw inputs and register their provenance.

Inputs   : configs/scrnaseq.yaml  (accession, base URL, file names)
           network access to ftp.ncbi.nlm.nih.gov
Outputs  : data/raw/GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz
           data/raw/GSE120575_patient_ID_single_cells.txt.gz
           data/metadata/SOURCES.md   (one registered row per file)
Env      : scrna   (environment/env-scrna.yml)

Re-running is safe. A file already present with the expected checksum is left
alone; nothing in data/raw is ever overwritten. Downloaded files are made
read-only (WORKSPACE.md rule 1).

    python workflows/00_download_data.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import stat
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

CHUNK = 1 << 20  # 1 MiB read block for hashing and streaming download


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    """Stream ``url`` to ``dest`` via a temporary file, then make it read-only."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:
        total = int(resp.headers.get("Content-Length", 0))
        got = 0
        while block := resp.read(CHUNK):
            out.write(block)
            got += len(block)
            if total:
                print(f"\r    {got / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    os.replace(tmp, dest)
    dest.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 444: raw data is read-only


def register(sources_md: Path, rows: dict[str, tuple[str, str, str, str]]) -> None:
    """Insert or refresh one table row per raw file in data/metadata/SOURCES.md.

    ``rows`` maps filename -> (source, obtained, checksum, notes). Rows for
    files this script does not manage are preserved untouched.
    """
    text = sources_md.read_text()
    lines = text.splitlines()
    header_i = next(i for i, ln in enumerate(lines) if ln.startswith("| File |"))
    sep_i = header_i + 1

    existing: dict[str, str] = {}
    order: list[str] = []
    for ln in lines[sep_i + 1:]:
        if not ln.startswith("|"):
            continue
        # Filenames are written inside backticks; strip them so the key
        # matches the plain filename used below. Without this the lookup
        # misses on a rerun and every row is appended a second time.
        key = ln.split("|")[1].strip().strip("`")
        if key.startswith("_("):  # the "(none yet)" placeholder
            continue
        existing[key] = ln
        order.append(key)

    for fname, (src, obtained, checksum, notes) in rows.items():
        existing[fname] = f"| `{fname}` | {src} | {obtained} | `{checksum}` | {notes} |"
        if fname not in order:
            order.append(fname)

    out = lines[: sep_i + 1] + [existing[k] for k in order] + [""]
    sources_md.write_text("\n".join(out) + "\n")


def main() -> int:
    cfg = load_config("scrnaseq")
    P = paths()
    P.raw.mkdir(parents=True, exist_ok=True)

    ds = cfg["dataset"]
    today = dt.date.today().isoformat()
    notes = {
        "expression": f"{ds['expression_unit']} matrix, genes x cells, as released by the authors",
        "annotation": "per-cell sample, patient, timepoint, therapy and response labels",
    }

    rows: dict[str, tuple[str, str, str, str]] = {}
    for key, fname in ds["files"].items():
        dest = P.raw / fname
        url = f"{ds['base_url']}/{fname}"
        if dest.exists():
            print(f"  present, not re-downloading: {fname}")
        else:
            download(url, dest)
        digest = sha256(dest)
        size_mb = dest.stat().st_size / 1e6
        print(f"  {fname}  {size_mb:.1f} MB  sha256 {digest[:16]}...")
        rows[fname] = (
            f"[{ds['accession']}]({ds['base_url']}/{fname})",
            today,
            digest,
            notes[key],
        )

    register(P.metadata / "SOURCES.md", rows)
    print(f"\nregistered {len(rows)} file(s) in {P.metadata / 'SOURCES.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
