# WORKSPACE.md — how work is done in this repository

**Read this before doing anything in this project.** It applies to the human
and to any AI agent working here. Everything else (`AGENTS.md`, `CLAUDE.md`,
the Claude Science project instructions) points back to this file so there is
exactly one source of truth.

The standard this repo is held to: *a stranger with this repository and no
access to the chat transcript can reproduce every number and every figure.*
A correct conclusion that cannot be reconstructed is not a finished analysis.

---

## 1. Layout

| Path | Contents | Tracked? | Mutable? |
|---|---|---|---|
| `data/raw/` | original inputs, exactly as obtained | no (provenance only) | **never** |
| `data/metadata/` | sources, checksums, sample sheets | yes | append |
| `data/processed/` | derived data, made by code | no | regenerate only |
| `src/` | reusable importable functions | yes | yes |
| `workflows/` | numbered scripts: raw -> results/figures | yes | yes |
| `configs/` | every parameter, in YAML | yes | yes |
| `results/` | tables, statistics, model output | yes (text) | regenerate only |
| `figures/` | generated plots | yes | regenerate only |
| `reports/` | write-ups and `DECISIONS.md` | yes | append |
| `tests/` | pytest checks | yes | yes |
| `environment/` | per-step conda specs and lock files | yes | yes |

## 2. Hard rules

1. **Raw data is read-only.** Never edit, rename, or overwrite anything in
   `data/raw/`. Corrections are scripts that write to `data/processed/`.
2. **Every raw input is registered** in `data/metadata/SOURCES.md` with its
   source URL or accession, the date obtained, and a SHA-256 checksum.
3. **No hard-coded parameters.** Thresholds, counts, resolutions, seeds, and
   paths live in `configs/*.yaml`. Code reads the config; code does not
   contain the number.
4. **Set and record the random seed** for every stochastic step. The seed is a
   config value, not a literal buried in a function call.
5. **Each workflow step is independently runnable** and declares its inputs and
   outputs at the top of the file. No step may rely on state left in memory by
   another step.
6. **The whole analysis reruns with one command** from a clean checkout. If it
   does not, it is broken.
7. **Record the environment.** Every step names the conda environment it runs
   in; the spec and resolved versions are in `environment/`.
8. **Every figure and every table is produced by a script in `workflows/`.**
   Nothing is made by hand, in an ad-hoc chat session, or in an untracked
   notebook.
9. **Log decisions in `reports/DECISIONS.md`** as they are made — what was
   chosen, what the alternatives were, and why. See section 4.
10. **Commit after each meaningful step** with a message saying what changed
    and why. The history is part of the deliverable.

## 3. Statistical standards

These are the questions this project must be able to answer about any result
it reports:

- **What is the experimental unit?** For single-cell data the unit is almost
  always the *patient or sample*, not the cell. Cells from one patient are not
  independent replicates; treating them as such inflates significance by orders
  of magnitude. Aggregate to the sample level (pseudobulk) or use a model with
  a patient-level random effect, and say which was done.
- **How many biological replicates are there, really?** State n at the level of
  the experimental unit, not the cell count.
- **Is the effect of interest confounded?** Check treatment against batch,
  sequencing run, processing date, and tissue site before interpreting
  anything. If they are confounded, say so rather than reporting the p-value.
- **What was filtered, and how many objects were removed at each step?** Record
  counts before and after every filter.
- **Was the test applied to the thing the figure shows?** The statistic and
  the plot must describe the same comparison on the same units.

A p-value is reported together with the model, the unit, and n. Never alone.

## 4. The decision log

`reports/DECISIONS.md` is append-only and holds one entry per consequential
choice:

    ## YYYY-MM-DD  <short title>
    Decision:    what was chosen
    Alternatives: what else was considered
    Reason:      why
    Affects:     which config keys / workflow steps / figures

Things that count as consequential: QC thresholds, normalization method,
which cells or samples were excluded, the clustering resolution, the
statistical model and its unit of analysis, and any deviation from these rules.

## 5. Environments

Small, per-step environments — `environment/env-<step>.yml` — not one large
environment holding every package. Pin versions. After creating an
environment, capture the resolved versions to `environment/env-<step>.lock.txt`.

## 6. Instructions for AI agents working in this repo

- Read this file and `reports/DECISIONS.md` before proposing an analysis.
- State the plan before executing it: inputs, outputs, parameters, and which
  config keys you will add or change.
- Put new parameters in `configs/` rather than inlining them, even for a
  one-off run.
- When you make a consequential choice, append to `reports/DECISIONS.md` in the
  same change that implements it.
- Do not report a result you have not computed in this repository, and do not
  present a number from a chat session that is not reproducible from a script
  here.
- If you cannot satisfy a rule, say so explicitly instead of working around it.
- Prefer editing an existing workflow step over creating a parallel variant.
