---
name: reproducible-workflow-step
description: "Add or revise a numbered analysis step in a reproducible-science repository governed by a WORKSPACE.md contract. Covers the step script template with its Inputs/Outputs/Env header, moving every threshold into configs/, recording filter counts, choosing the experimental unit, appending a DECISIONS.md entry in the same commit, and verifying that a full rerun regenerates every tracked output byte-identically. Use when adding an analysis step, porting an analysis into the repo, or auditing an existing step against the repository rules."
---

# Reproducible workflow step

House procedure for the BIOINFO291 repository (and any repo laid out the same
way). The standard the repo is held to: *a stranger with the repository and no
access to the chat transcript can reproduce every number and every figure.*

Read `WORKSPACE.md` and `reports/DECISIONS.md` before proposing an analysis.
`WORKSPACE.md` is the contract; this skill is how to satisfy it.

## The contract a step must satisfy

1. **Declares its interface.** A docstring header naming `Inputs`, `Outputs`
   and `Env`, so the step is readable without running it.
2. **Owns no numbers.** Every threshold, count, resolution, gene panel and
   seed comes from `configs/*.yaml`. If you typed a number into the script,
   it belongs in the config.
3. **Independently runnable.** Reads its inputs from disk, writes its outputs
   to disk. No step may depend on state another step left in memory.
4. **Counts what it removes.** Any filter writes rows-before and rows-after to
   a table in `results/`.
5. **Logs its reasoning.** A consequential choice gets a `DECISIONS.md` entry
   in the *same commit* that implements it.
6. **Reruns clean.** After `bash workflows/run_all.sh`, `git status` is empty.
   A changed output means something is unseeded or depends on wall-clock time.

## Procedure

1. **Read the rules and the log.** `WORKSPACE.md`, then `reports/DECISIONS.md`
   so you do not re-litigate a settled choice.
2. **State the plan before writing code**: inputs, outputs, parameters, and
   which config keys you will add or change.
3. **Add the parameters to `configs/` first.** Writing the config before the
   code makes rule 2 the default rather than a cleanup pass.
4. **Scaffold the step** with `scaffold_step(...)` (see below), then fill in
   `main()`.
5. **Run it. Read the output.** Check counts against an external expectation
   (a published cohort size, a prior step's total) and assert them in code so
   a silent parsing error fails loudly.
6. **Inspect every figure you generate.** Verify each claim-title against the
   data before accepting it; a title asserting a pattern the numbers do not
   support is a defect, not a style issue.
7. **Append the `DECISIONS.md` entry** with `decision_entry(...)`.
8. **Commit** the script, the config change and the decision entry together,
   with a message saying what changed and why.
9. **Verify**: `pytest -q`, then a full `run_all.sh` and `git status` empty.

## Statistical standards

Before reporting any result, answer these in the report or the decision log:

- **What is the experimental unit?** For single-cell data it is almost always
  the patient or sample, not the cell. Check whether the label you are testing
  is actually recorded at that level: a per-lesion or per-biopsy label does not
  become a patient label by aggregation, and subjects whose own samples
  disagree have no defined label at all.
- **How many biological replicates, really?** State n at the level of the unit.
- **Is the effect confounded?** Cross-tabulate the grouping variable against
  batch, processing date, protocol, sorting strategy and sample size, and write
  that table *before* reading the result.
- **Do the files agree?** When a dataset ships more than one description of the
  same samples, compare them and reconcile every disagreement. Metadata a
  release drops is frequently the confounder.
- **Was the test applied to the thing the figure shows?** Same comparison, same
  units.
- **Is a reported performance figure cross-validated?** Selecting features on
  all samples and scoring those same samples measures fit, not generalisation.
  Report the honest number as the headline and the in-sample number beside it.

A p-value is reported with its model, its unit and n. Never alone.

## Figures

Project style lives in `src/plotting.py` and is imported by the step, so the
repository renders its figures with no editor or agent in the loop. Never make
a figure by hand or in an untracked notebook.

## Reference

- `step_template()` returns the skeleton this skill installs.
- `scaffold_step(repo, number, slug, purpose, inputs, outputs)` writes
  `workflows/NN_slug.py`.
- `decision_entry(title, decision, alternatives, reason, affects)` returns a
  correctly formatted log entry to append to `reports/DECISIONS.md`.
- `audit_steps(repo)` reports which steps violate rules 1 and 2.
