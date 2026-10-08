# tests — checks that the pipeline still does what it claims

Run with `pytest` from the repo root.

Worth testing: functions in `src/` with known inputs/outputs, config loading,
and shape/sanity assertions on processed data (no NaNs where there should be
none, cell counts conserved, etc.).
