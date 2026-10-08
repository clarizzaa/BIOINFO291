# src — reusable functions

Importable code: loading, QC, normalization, plotting helpers, statistics.

Rules:
- No hard-coded parameters. Functions take them as arguments; the values live
  in `configs/*.yaml`.
- No top-level side effects (no file reads/writes on import).
- Anything here that a workflow depends on should have a test in `tests/`.
