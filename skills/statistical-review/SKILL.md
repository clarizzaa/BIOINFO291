# Reviewing a paper's statistics against its own data

A paper's statistics are a contract with its readers. The rules are in
**`docs/statistical-review.md`** — sixteen enforced (S1–S16) and an appendix of
reporting items (R1–R7). This skill does not restate them; it turns them into
procedure. Read the rule when a step below cites it.

The input is always two things: **the paper and the data the paper was built
from.** A review with only the paper can report that a claim is *unverifiable*;
it cannot report that a claim is *unsupported*. That asymmetry is the whole
design, so a paper whose deposit cannot be obtained is not reviewed.

`kernel.py` loads automatically with this skill.

---

## The shape of a review

A review is not an opinion about a paper. It is an attempt to **reproduce every
number the paper prints**, followed by an attempt to **re-run the analysis the
way the design requires**, followed by an honest statement of what is left.

The order matters. Reproduce first. A paper whose numbers do not reproduce is a
different problem from a paper whose numbers reproduce but answer the wrong
question, and the second is far more common. Most papers you review will be
arithmetically perfect.

---

## The procedure

### 1. Register the paper and its data

`workflows/30_fetch_papers.py <slug>` from the `papers:` registry in
`configs/statreview.yaml`. Checksums go in `data/metadata/SOURCES.md`; nothing
in `data/raw/` is ever edited.

Some repositories refuse automated downloads (Dryad returns 401 on its API
route and 403 on its file route). Place the files by hand and let the recorded
SHA-256 pin them. **Do not defeat a site's bot protection** — a checksum makes a
hand-placed file exactly as verifiable as a downloaded one.

### 2. Look at the data before computing anything

`workflows/31_describe_deposit.py <slug>` prints every sheet, its shape, its
columns and its first rows. Do this before forming any hypothesis about the
analysis.

**Deposited spreadsheets are not tidy.** Expect several independent blocks
pasted side by side in one sheet, summary rows interleaved inside the data
region, and the column the paper actually tested sitting three columns to the
right of the raw measurements. Reconcile every n in the paper against a count in
a file before you trust any mapping (S4, R4).

### 3. Find the unit the tests actually counted

This is the single highest-yield step, and `n_from_statistic` exists for it.
Work out the n each reported statistic implies and compare it with the number of
independently assigned subjects (S3, S5):

- A Kruskal-Wallis on three groups of 12 where the paper describes 24 subjects
  is testing something other than subjects.
- A Wilcoxon *V* of 7108 implies about 120 paired observations
  (`V ≤ n(n+1)/2`), not 43 subjects.
- A regression whose residual df is 66 was not fitted on 24 animals.

Where the two differ, the deposit usually contains both: the subject-level rows
*and* the aggregated column that was tested. Re-run the comparison on the
subjects and report both.

### 4. Reproduce the reported statistics

Independently first, then read the authors' analysis script only to resolve a
disagreement. A statistic that will not reproduce until you have read their code
is a finding about the paper's reporting, not about your attempt.

Reproducing R from Python needs its conventions, which papers rarely state:

| R | convention `kernel.py` implements |
|---|---|
| `wilcox.test(paired=TRUE)` | drops zero differences; exact distribution when n < 50 with no ties, else normal approximation **with** continuity correction; `V` is the sum of ranks of *positive* differences, so argument order matters |
| `summary.glm` (gaussian) | *t* on residual df, not *z*; AIC counts the dispersion parameter, so R's AIC is 2.000 above a statsmodels fit of the same model |
| `dunn.test` | prints a **one-tailed** p by default — a reported value that is exactly half your two-sided value is this, not a discrepancy (S6) |
| `kruskal.test`, `wilcox.test` | tie corrections differ between implementations; check before reporting a mismatch |

Call `wilcox_test_R` and `glm_p_rlike` rather than reimplementing these.

### 5. Count the family

`collect_family` and `correct_family`. Every p-value the Results report, plus
every test the Methods imply (S13). Report Bonferroni *and* Benjamini-Hochberg:
they answer different questions and neither replaces the other.

A paper that says "unreported comparisons were non-significant" has conceded a
larger family without sizing it. Say so, and say that your count is a lower
bound (S14).

### 6. Re-analyse, then say what survives

Apply the unit correction and the family correction **together**. Either alone
understates the problem: p-values are often small *because* the unit is wrong,
so correcting a family of inflated values barely moves them.

Then write section 5 of the review — the sentences the data *do* support. A
review that lists failures without saying what the evidence shows has not
finished its job.

### 7. Figures

At least one recomputation figure per blocking finding, made by a script in
`workflows/`, following `docs/figure-contract.md` in full and carrying its
`.contract.json` sidecar. Load the `figure-contract` skill for that; this skill
does not duplicate it. Hand each figure to `agents/figure-reviewer/` before the
review ships.

The two that recur:

- **The unit comparison** — the same comparison at the paper's unit and at the
  defensible unit, on shared scales (C2), both n stated with their noun (C8),
  every unit drawn (C9), and each panel's interval defined *in the image* with
  the unit it was taken over (C10).
- **The family** — every reported p-value before and after correction, with the
  threshold drawn. Name the quantity in each column: a q-value on an axis
  labelled "p-value" is a C5 violation.

A review figure may not use a device the figure contract forbids, even to
demonstrate that the paper used it.

### 8. Write the record

`reports/statistical_reviews/<slug>/` with `REVIEW.md` and `review.json` in the
format `docs/statistical-review.md` specifies. One record per **claim**, not per
paper. A paper with one unsupported claim and nine sound ones is reported that
way.

---

## Judgement

**Report what passes.** A rubric that only ever lists failures cannot be
audited. If S11's resolution floor is comfortably below every reported p-value,
say so; if the sign test agrees with the signed-rank test, say that the
surviving claim does not depend on the symmetry assumption.

**Separate the procedure from its outcome.** A normality pre-test used as a
test-selector (S7) breaks the rule even when both tests give the same answer.
Record the finding and record that it changed no conclusion. Both are true and
the reader needs both.

**Quantify your own caveats.** "No result survives" is a weaker statement when
the nearest value is q = 0.0505 against a 0.05 threshold. Put the distance in
the review and on the figure.

**A finding is cited, not argued.** Every finding names an S, C or R identifier
and quotes what was observed — in the paper or computed from the data. An
observation that restates the rule is not an observation.

**Reproduction is not endorsement, and failure to reproduce is not fraud.** Most
discrepancies are software conventions. Exhaust those before writing a finding.

---

## In this repository

- Rules: `docs/statistical-review.md`. Reviewer: `agents/statistical-reviewer/`.
  Both cite the same identifiers; neither restates them.
- Parameters — α, correction methods, iteration counts, seed, the n below which
  the p-floor is enumerated — are config values in `configs/statreview.yaml`,
  read via `src/config.py` (WORKSPACE.md rule 3).
- Every table and figure is produced by a numbered script in `workflows/`
  (rule 8). Computing a review number in a chat session and pasting it into the
  write-up is the one thing this repository does not permit.
- Give every test a stable `test_id` in every table. Joining recomputation
  tables on human-readable labels silently drops rows when a label is written
  two ways; that is how the first draft of a review figure came to claim 11
  tests where there were 23.
- Worked example: `reports/statistical_reviews/wang2026-conspecific-odors/`,
  with `workflows/30`–`33`.
