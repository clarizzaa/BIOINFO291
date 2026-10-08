# configs — every parameter, in one visible place

YAML only. If a number influences a result, it lives here, not in the code:
filtering thresholds, number of PCs, clustering resolution, random seeds,
file paths, model formulas.

Why: you can see the entire analysis setup without reading code, and a
parameter change is a one-line, reviewable git diff.
