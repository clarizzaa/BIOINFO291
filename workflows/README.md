# workflows — raw data to final outputs

Numbered, ordered scripts. Each one reads a config, reads from `data/`, and
writes to `data/processed/`, `results/`, or `figures/`.

    01_download.py      raw data in, provenance recorded
    02_qc.py            filtering and QC figures
    03_normalize.py     ...

Rules:
- Each step is runnable on its own and states its inputs and outputs at the top.
- Running them in order from a clean checkout reproduces every figure.
- No interactive state. A script must not depend on something another script
  left in memory — that is the notebook cell-order trap.
