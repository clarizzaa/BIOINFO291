#!/usr/bin/env python
"""Step 30 - obtain a reviewed paper's PDF and data deposit, and register them.

Inputs   : configs/statreview.yaml  (the `papers:` registry)
           network access to datadryad.org and the publisher
Outputs  : data/raw/papers/<slug>/   (deposit files + paper.pdf)
           data/metadata/SOURCES.md  (one registered row per file)
Env      : python   (stdlib + pyyaml only)

A statistical review needs the paper *and* the data the paper was built from
(docs/statistical-review.md: a blocking finding must be demonstrated by
recomputation, so a paper whose deposit cannot be obtained is not reviewed).
This step fetches both and records their provenance.

Re-running is safe. A file already present is left alone; nothing in
data/raw is ever overwritten. Downloaded files are made read-only
(WORKSPACE.md rule 1).

    python workflows/30_fetch_papers.py                 # every confirmed paper
    python workflows/30_fetch_papers.py <slug>          # just one
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import stat
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import load_config, paths  # noqa: E402

CHUNK = 1 << 20
DRYAD_API = "https://datadryad.org/api/v2"
# Dryad rejects the default urllib agent on the file-download redirect.
AGENT = "BIOINFO291-statistical-review/1.0 (teaching repository; +WORKSPACE.md)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def download(url: str, dest: Path) -> None:
    """Stream ``url`` to ``dest`` via a temporary file, then make it read-only."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  downloading {dest.name}")
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp, open(tmp, "wb") as out:
        while block := resp.read(CHUNK):
            out.write(block)
    os.replace(tmp, dest)
    dest.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def dryad_files(data_doi: str) -> list[dict]:
    """Resolve a Dryad DOI to its current version's file list.

    Dryad's dataset endpoint takes the DOI percent-encoded *twice* over: the
    colon and slashes are encoded, and the result is then a path segment.
    """
    quoted = urllib.parse.quote(f"doi:{data_doi}", safe="")
    dataset = get_json(f"{DRYAD_API}/datasets/{quoted}")
    version_href = dataset["_links"]["stash:version"]["href"]
    listing = get_json(f"https://datadryad.org{version_href}/files")
    return listing["_embedded"]["stash:files"]


def register(sources_md: Path, rows: dict[str, tuple[str, str, str, str]]) -> None:
    """Insert or refresh one table row per raw file in data/metadata/SOURCES.md.

    Rows for files this script does not manage are preserved untouched. Keys
    are the path relative to data/raw/, so two papers may deposit files of the
    same name without colliding.
    """
    lines = sources_md.read_text().splitlines()
    header_i = next(i for i, ln in enumerate(lines) if ln.startswith("| File |"))
    sep_i = header_i + 1

    existing: dict[str, str] = {}
    order: list[str] = []
    for ln in lines[sep_i + 1:]:
        if not ln.startswith("|"):
            continue
        key = ln.split("|")[1].strip().strip("`")
        if key.startswith("_("):
            continue
        existing[key] = ln
        order.append(key)

    for rel, (src, obtained, checksum, notes) in rows.items():
        existing[rel] = f"| `{rel}` | {src} | {obtained} | `{checksum}` | {notes} |"
        if rel not in order:
            order.append(rel)

    out = lines[: sep_i + 1] + [existing[k] for k in order] + [""]
    sources_md.write_text("\n".join(out) + "\n")


def fetch_paper(paper: dict, raw_root: Path, today: str) -> dict:
    """Fetch one paper's deposit. Returns SOURCES.md rows keyed by relative path."""
    slug = paper["slug"]
    dest_dir = raw_root / slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    rows: dict[str, tuple[str, str, str, str]] = {}

    print(f"\n{slug}  ({paper['citation']})")

    # The article PDF. Scientific Reports is open access; the publisher URL is
    # recorded whether or not the download succeeds, so the provenance of a
    # hand-placed copy is still the publisher.
    pdf = dest_dir / "paper.pdf"
    pdf_url = (
        f"https://www.nature.com/articles/{paper['paper_doi'].split('/')[-1]}.pdf"
        if paper.get("paper_doi", "").startswith("10.1038/")
        else None
    )
    if pdf.exists():
        print("  present, not re-downloading: paper.pdf")
    elif pdf_url:
        try:
            download(pdf_url, pdf)
        except Exception as exc:  # noqa: BLE001 - provenance recorded either way
            print(f"  could not download paper.pdf ({exc.__class__.__name__}: {exc})")
            print("     place the publisher's PDF at this path by hand and re-run")
    if pdf.exists():
        rows[f"papers/{slug}/paper.pdf"] = (
            f"[doi:{paper['paper_doi']}](https://doi.org/{paper['paper_doi']})",
            today,
            sha256(pdf),
            "article PDF as published (open access)",
        )

    # The data deposit.
    if paper.get("data_source") != "dryad" or not paper.get("data_doi"):
        print("  no resolved data deposit; nothing to fetch")
        return rows

    for entry in dryad_files(paper["data_doi"]):
        name = entry["path"]
        dest = dest_dir / name
        if dest.exists():
            print(f"  present, not re-downloading: {name}")
        else:
            download(f"https://datadryad.org{entry['_links']['stash:download']['href']}", dest)
        digest = sha256(dest)
        print(f"  {name:<28} {dest.stat().st_size / 1e3:8.1f} kB  sha256 {digest[:16]}...")
        rows[f"papers/{slug}/{name}"] = (
            f"[doi:{paper['data_doi']}](https://doi.org/{paper['data_doi']}) (Dryad)",
            today,
            digest,
            f"deposited by the authors of {slug}",
        )
    return rows


def main(argv: list[str]) -> int:
    cfg = load_config("statreview")
    P = paths()
    raw_root = P.root / cfg["outputs"]["raw"]
    today = dt.date.today().isoformat()

    wanted = set(argv[1:])
    selected = [
        p for p in cfg["papers"]
        if (p["slug"] in wanted if wanted else p.get("status") == "confirmed")
    ]
    if not selected:
        print("nothing selected. confirmed papers in configs/statreview.yaml:")
        for p in cfg["papers"]:
            print(f"  {p['slug']:<34} status={p.get('status')}")
        return 1

    rows: dict[str, tuple[str, str, str, str]] = {}
    for paper in selected:
        rows.update(fetch_paper(paper, raw_root, today))

    register(P.metadata / "SOURCES.md", rows)
    print(f"\nregistered {len(rows)} file(s) in {P.metadata / 'SOURCES.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
