# figures — generated plots

Every figure is produced by a script in `workflows/`. No figure is made by
hand, in a notebook, or dragged out of a chat window.

Each figure file should be traceable to the script and config that made it.

## Layout

Figures are filed per dataset, one subdirectory each, so this directory does
not become a flat pile shared across weeks:

    figures/chickweight/    week-2 ChickWeight figures, each with its sidecar
    figures/*.png           week-1 melanoma (GSE120575) figures

The week-1 figures sit at the root because they predate this arrangement and
their workflow steps were deliberately not reopened; see `PRE_CONTRACT.txt`.

## Sidecars

Every figure made since `docs/figure-contract.md` carries a
`<name>.contract.json` beside it, declaring the question, the claim, the
experimental unit, n at that unit, what any interval means, transformations,
exclusions and the script that made it. `save_figure()` writes both and
refuses to write a figure whose declaration is incomplete; a pytest check
enforces the same across the whole directory tree.

The nine figures listed in `PRE_CONTRACT.txt` predate the contract and are
exempt from the sidecar requirement, and from nothing else.
