# The statistical review contract

A paper's statistics are a contract between its authors and its readers. The
authors promise that the numbers printed in the text were computed from the
deposited data, that each test's null hypothesis is the one the claim denies,
that the units counted were independent, and that the p-values shown account
for the p-values computed. The reader brings the data, the code, and the
willingness to recompute.

Review under this contract is not peer review. It does not judge whether the
question is interesting, whether the experiment was worth doing, or whether
the conclusion is true. It judges one thing: **whether the stated evidence
supports the stated claim**, and it answers by recomputation wherever
recomputation is possible.

This file states that contract as numbered rules. It is the single source for
statistical standards in this repository: the review procedure
(`skills/statistical-review/`) tells an author how to run a review against
these rules, and the review subagent (`agents/statistical-reviewer/`) reports
which ones a paper broke. Neither restates the rules; both cite these
identifiers.

Source: BIOINFO291 / CHEM291, *Practical Data Analysis in Systems Biology*,
lecture 3 (using the language of probability to make confidence statements).
Its companion for figures is [`docs/figure-contract.md`](figure-contract.md);
where a finding is about the drawing rather than the inference, cite a `C`
rule from that file instead of duplicating it here.

---

## Two tiers

**Enforced rules (S1–S16).** A violation means the paper's *stated evidence
does not support its stated claim*: a reader who trusts the text ends up
believing something the data do not show. These are checked on every claim
and a violation blocks it.

**Reporting items (appendix).** Real problems worth fixing, but a reader with
the deposited data can still reach the correct conclusion. Reported, never
blocking.

A rule fires against a **claim**, not against a paper. A paper with one
blocking claim and nine sound ones is reported exactly that way; the verdict
is about the claim set, and the summary says which claims survive.

The enforced rules are grouped under the six promises a statistical claim
makes.

---

## Sampling — the sample supports the population the claim names

### S1 — The population is named and the sampling route is described

**Promise.** The reader can say what group the claim is about and how members
of that group came to be in the sample.

**Fails when.** The claim generalizes to a population the paper never defines
("dogs", "patients", "cells") while the sample is a convenience set recruited
through one channel. Volunteers, owner-recruited subjects, clinic walk-ins, or
a single facility's animals are described as though drawn at random from the
species. The sampling frame is absent and the inferential target is left to the
reader.

**Check.** Name the population in the claim's own words. Name the route by
which subjects entered the sample. Could a member of the stated population not
in this sample have been recruited? If the answer is no, the claim is about the
sample, and must say so.

**Recomputation.** Not recomputable. Judged from the text, and reported with
the population the evidence does support.

---

### S2 — Confounds are checked, and a null check is not a clearance

**Promise.** Variables that moved with the comparison — batch, site, date,
room, operator, protocol version, equipment — were examined, and the
examination had the power to find something.

**Fails when.** A known design change (a protocol added partway through, a room
swap, a reagent lot) is entered as a covariate and dismissed with "p > 0.05",
with no estimate, no interval, and no power to detect an effect the size that
would matter. Confounds are listed in the limitations and not tested at all.
The comparison of interest is perfectly or near-perfectly aligned with a
nuisance variable, so the two cannot be separated, and the paper reports the
p-value anyway.

**Check.** Tabulate the comparison against every nuisance variable the methods
mention. Is any cell empty or near-empty? For each confounder check reported as
null: what is the estimate and its interval, and does the interval exclude an
effect as large as the claimed one? A confounder check is informative only when
it could have failed.

**Recomputation.** Recomputable when the nuisance variables are in the deposit.
Cross-tabulate, and report the confounder estimate with its interval rather
than its p-value.

---

## Unit — the statistic counts independent units

### S3 — The test is run at the experimental unit

**Promise.** The n entering the test counts things that could have varied
independently, not repeated observations of the same thing.

**Fails when.** Cells from three cultures are tested as 36 independent
observations. Repeated measurements of one subject across time are pooled as
though each were a separate subject. Measurements are averaged *across*
subjects and the test is then run over the within-subject structure that
remains — time bins, trials, sample points — so n becomes the number of bins
and the subjects disappear from the denominator. Pairs, litters, cages, or
dyads are counted as individuals.

**Check.** Name the experimental unit: what was independently assigned,
sampled, or randomized? Count those. Then read the reported degrees of freedom,
n, or test statistic and recover the n the test actually used. If the two
differ, the test is not about the unit the claim is about.

**Recomputation.** Recomputable from the deposit. Re-run the same comparison at
the experimental unit and report both results side by side. A claim whose
significance does not survive the change of unit is blocking under this rule.

---

### S4 — n is stated at that unit, per group

**Promise.** The reader can find how many independent units each group
contributes without inferring it from a test statistic.

**Fails when.** n is given for the pooled sample but not per group. n drifts
between the methods, the results, and the figure captions with no stated
reason. The count given is of observations, trials, or cells while the test is
at the subject level, or the reverse. Dropouts move n between analyses and the
paper does not say which analysis used which n.

**Check.** For every claim, is the per-group n printed at the unit the test
used? Reconcile every n in the paper against the deposited data. Unexplained
disagreement is a finding under this rule even when the direction of the
conclusion is unaffected.

**Recomputation.** Always recomputable. Count the rows.

---

### S5 — Repeated measures enter the model as repeated measures

**Promise.** Correlation between observations of the same unit is represented,
not discarded.

**Fails when.** Each subject contributes a measurement in every condition and
the conditions are compared with a test for independent groups — a Kruskal-
Wallis, a one-way ANOVA, a Mann-Whitney — so the within-subject pairing that
would have increased precision is thrown away and the independence assumption
is violated at the same time. A mixed model is fitted with no subject random
effect. Pairing is used for some comparisons in a paper and ignored for others
on the same data with no stated reason.

**Check.** Does every unit appear in more than one condition, or more than
once? If so, does the test name the pairing — a signed-rank, a paired t, a
Friedman, a random effect for subject? An independent-groups test on
within-subject data is blocking regardless of which direction the bias runs.

**Recomputation.** Recomputable. Re-run with the pairing and report the change.

---

## Model — the null that was tested is the null the claim denies

### S6 — The test's null is the one the claim denies

**Promise.** Rejecting the null licenses the sentence the paper writes.

**Fails when.** A test of a difference in distributions is reported as a
difference in means. A rank-sum result is written as a difference in medians. A
significant interaction is described as a main effect, or a significant main
effect as an interaction. An omnibus test across three or more groups is
reported as though it identified which groups differ. A test of "the odor
affects behavior" is run as "condition is associated with the summary score"
and written as "the odor caused the behavior".

**Check.** Write the test's null hypothesis in one sentence, in the test's own
terms. Write the claim's negation in one sentence. Are they the same sentence?
If the test is omnibus, does any post-hoc comparison exist for the specific
contrast the claim states?

**Recomputation.** Partly recomputable: the specific contrast the claim needs
can usually be run.

---

### S7 — Assumptions are defended by design, not chosen by a pre-test

**Promise.** The choice of test was made for reasons that survive the data
being different.

**Fails when.** A normality test (Shapiro-Wilk, Kolmogorov-Smirnov,
D'Agostino) is used as a switch: parametric if p > 0.05, nonparametric
otherwise. This makes the reported error rate a function of a first test's
outcome, is underpowered at exactly the sample sizes where normality matters,
and over-rejects at exactly the sizes where it does not. Also fails when a
transformation is chosen after seeing which one gives the smaller p-value, or
when normality is checked on the pooled sample rather than within group (for
independent groups) or on the paired differences (for paired data).

**Check.** Does the methods section name a pre-test as the selector? On what
quantity was the distributional check performed — pooled values, within-group
values, or paired differences? Was a transformation chosen before or after
seeing the outcome?

**Recomputation.** Recomputable. Run the comparison under both the parametric
and the rank-based alternative and report whether the conclusion depends on the
choice. When it does not, this is a reporting item rather than a blocking one.

---

### S8 — The reported spread is the one the claim needs, and it is named

**Promise.** The reader knows whether an interval describes the spread of
observations or the uncertainty of an estimate, and at what n.

**Fails when.** An interval appears with no definition. SEM is reported where
the claim is about the variability of individuals, or SD where the claim is
about the precision of a mean. An SEM is computed over a within-subject
structure — time bins, trials, technical replicates — so it shrinks with the
number of repeats rather than with the number of subjects, and is then
presented as the uncertainty in a between-group comparison. The n used for the
interval differs from the n the claim states.

**Check.** For every interval in text or figure: is it named, is its n stated,
and is that n at the experimental unit? Recompute it. An SEM over 12 time bins
and an SEM over 41 subjects differ by a factor the reader cannot see.

**Recomputation.** Always recomputable. Report both intervals when they differ.

---

### S9 — Rank-based results are read as statements about ordering

**Promise.** A rank test's conclusion is stated in terms the test can support.

**Fails when.** Mann-Whitney is reported as a test of equal medians — two
groups can have identical medians and a strongly significant rank-sum result.
A signed-rank test is applied to paired differences that are not symmetric
about their null value, where large magnitudes carry one sign; the sign test
remains valid there and the signed-rank test does not. A significant rank
result is converted to an effect size in original units. Rank results are used
to argue the *size* of an effect, which ranks discard by construction: changing
the largest observation from 100 to 10,000 leaves every rank, and the p-value,
unchanged.

**Check.** Which rank test, and what is its null? For a signed-rank claim,
inspect the distribution of paired differences for symmetry. For a rank-sum
claim written as a median difference, compute both medians and the probability
of superiority; if the medians are equal or cross, the claim is wrong as
written. Is an effect size in original units being supported by a rank test?

**Recomputation.** Recomputable. Report the probability of superiority
(U / n₁n₂) alongside group medians, and the sign test beside the signed-rank
test where symmetry is doubtful.

---

### S10 — Resampling declares its exchangeability, its unit, and its scope

**Promise.** A permutation or bootstrap result names the computational
experiment it ran and why that experiment represents the null or the sampling
distribution.

**Fails when.** A permutation test shuffles labels across a structure the null
does not make exchangeable — shuffling condition across all rows of a
repeated-measures design, so the permuted null destroys the within-subject
pairing as well as the condition effect, and the p-value answers a question
nobody asked. The permutation unit is not stated. A bootstrap resamples rows
when the unit is the subject. A bootstrap interval is presented as a confidence
interval with no attention to bias, or with too few iterations to estimate the
tails it reports.

**Check.** What is permuted, within what blocks, and what would have to be true
for the permuted datasets to be as likely as the observed one under the null?
What is resampled in the bootstrap, and is the resampling unit the experimental
unit? How many iterations, and does the reported interval or p-value have the
resolution that many iterations can supply (see S11)?

**Recomputation.** Recomputable, and usually the most informative thing a
review can do: re-run the resampling with the correct unit and blocks.

---

## Resolution — the p-value can bear the weight placed on it

### S11 — The reported p-value is above the design's resolution floor

**Promise.** The quoted precision is attainable by the test on that many
observations.

**Fails when.** An exact test on a small sample quotes a p-value its support
cannot produce: with five nonzero pairs, the smallest two-sided sign-test
p-value is 2/32 = 0.0625, so "p < 0.05" is unattainable no matter what the
data show. A permutation p-value is quoted below 1/(N+1) for the N
permutations run, or quoted as "p < 0.001" from a thousand permutations where
the attainable minimum is 1/1001. A test's exact null distribution is
discrete and the paper reports a p-value between its atoms. Asymptotic
approximations are used at sample sizes where the exact distribution is
coarse, without saying so.

**Check.** For each exact or resampling-based test: enumerate the support, or
compute 1/(N+1). Is the reported value attainable? For claims near the
threshold, report the next attainable value on either side.

**Recomputation.** Always recomputable, and cheap. This check needs only n and
the test.

---

### S12 — A non-rejection is not an equivalence claim

**Promise.** Failure to reject is reported as absence of evidence, not as
evidence of absence.

**Fails when.** "No significant difference" becomes "the groups did not
differ", "the odor had no effect", or "X does not distinguish Y" in the
abstract or discussion. A null result is used as a premise for a further
argument. Two conditions are declared equivalent with no equivalence test, no
interval, and no smallest effect size of interest. A significant result in one
subgroup and a null in another are contrasted as a difference between
subgroups without testing the interaction.

**Check.** For every null result that carries weight in the argument: what is
the estimate and its confidence interval, and what effect sizes does the
interval still admit? Does the paper's own claimed effect size lie inside it?
If two subgroups are contrasted, was the interaction tested?

**Recomputation.** Recomputable. Report the interval and the effect sizes it
cannot exclude.

---

## Family — every p-value computed is accounted for

### S13 — The test family is declared and corrected

**Promise.** The reader can count the tests the paper ran and knows what the
reported thresholds mean across them.

**Fails when.** Dozens of tests are reported at α = 0.05 with no correction and
no statement that none was applied. The correction is applied within one table
but not across the paper's claim set. A family is defined after seeing the
results so that the significant findings fall outside it. Post-hoc comparisons
following an omnibus test are reported uncorrected. A correction is named in
the methods and the corrected values appear nowhere.

**Check.** Count every test whose p-value is reported, and every test the
methods imply was run. Define the family the claim belongs to and say why.
Apply both a familywise correction (Bonferroni: the probability that *any* of
these is a chance finding) and a false-discovery-rate correction (Benjamini-
Hochberg: an adaptive threshold admitting a stated fraction of false positives
among the called ones). Report which claims survive each.

**Recomputation.** Always recomputable from the reported p-values alone.

---

### S14 — Analytic freedom is declared

**Promise.** The reader knows what else was run, what was decided after seeing
the data, and which findings are exploratory.

**Fails when.** The paper states that unreported comparisons were
non-significant, which concedes a larger family without sizing it. Outcome
measures, groupings, exclusions, or covariates were chosen after inspecting
the data and are reported as though pre-specified. An analysis is described as
prompted by an observation in the data ("during coding, distinct postures were
observed, which prompted further investigation") and the resulting tests are
reported at the same α as the pre-specified ones. Subgroups appear only where
they were significant.

**Check.** Does the paper say how many comparisons were run in total? Are
post-hoc and exploratory analyses labeled as such, and held to a stated
standard? Is there a pre-registration, and does the analysis match it?
Exploratory analysis is legitimate; presenting it as confirmatory is not.

**Recomputation.** Not recomputable. Judged from the text, and sized against
the test count from S13.

---

## Claim — the sentence in the abstract is the one that was tested

### S15 — The claim's direction, magnitude, and subject are the tested ones

**Promise.** The abstract's sentence is the result, not an interpretation of
it.

**Fails when.** An association is written as a cause. A within-group change is
written as a between-group difference. A claim names a mechanism the design
cannot distinguish. The magnitude asserted is larger than the estimate, or is
asserted with no estimate at all. The claim is about a population the sample
does not represent (see S1). A result significant in one condition is
generalized to the construct the condition was meant to operationalize.

**Check.** Read the abstract's claims alone, without the results section. For
each, name the test that supports it and the comparison that test made. What
study design would be required to state the sentence as written? Is that the
design that produced the data?

**Recomputation.** Not recomputable. Judged by matching each abstract claim to
a test.

---

### S16 — Figure and test describe the same comparison on the same units

**Promise.** The statistic annotated on a figure was computed on what the
figure draws.

**Fails when.** Significance stars sit over bars summarizing one quantity while
the test was run on another — a figure of per-bin means annotated with a test
on subjects, or the reverse. The figure pools what the test separated. The
error bars are at one unit and the test at another (see S8). A comparison is
starred in the figure and absent from the results text, or present in the text
with a different p-value.

**Check.** For every annotated comparison in every figure: identify the test in
the text, the quantity plotted, and the n behind each. Do all three agree? Then
hand the figure to the figure contract — `docs/figure-contract.md` — and cite
`C` rules for anything about the drawing itself.

**Recomputation.** Recomputable. Rebuild the figure from the deposit at the
unit the test used, and at the unit the claim needs.

---

## Appendix — reporting items

Reported by the reviewer, never blocking.

- **R1** Exact p-values are given, not only thresholds; "p < 0.05" hides
  whether a result sits at 0.049 or 0.0001.
- **R2** Every test statistic is reported with its degrees of freedom or n, and
  with an effect size and interval, not a p-value alone.
- **R3** Software, package versions, and the random seed are named, so a
  stochastic result is reproducible.
- **R4** The deposited data is documented well enough to map every column to a
  variable in the methods, and every reported n to a count in a file.
- **R5** The deposited analysis code runs, and runs on the deposited data.
- **R6** Rounding is consistent, and reported statistics agree with the data to
  the precision printed.
- **R7** Figures and tables are numbered and referenced consistently, and every
  statistic in a caption also appears in the text.

---

## The review record

Every review produces a directory
`reports/statistical_reviews/<slug>/` containing:

| Path | Contents |
|---|---|
| `REVIEW.md` | the human-readable review, in the order below |
| `review.json` | the machine-readable findings; schema in `agents/statistical-reviewer/output_schema.json` |
| `figures/` | recomputation figures, each with its `.contract.json` sidecar |
| `recompute/` | the per-claim recomputation table written by the workflow script |

`<slug>` is `<first-author-surname><year>-<two-or-three-word-topic>`, all
lowercase, e.g. `wang2026-conspecific-odors`.

### The claim record

The unit of a review is the **claim**. Every claim gets one record, and every
record carries these fields — with an explicit `"not recomputable"` rather
than an omission:

| Field | Meaning |
|---|---|
| `id` | stable identifier within the review, e.g. `C3` |
| `claim` | the paper's assertion, verbatim, with its location |
| `test_as_stated` | the test the paper says it used, with its reported statistic and p-value |
| `unit_used` | the experimental unit the test actually counted, and that n |
| `unit_defensible` | the unit the claim requires, and that n |
| `recomputed` | the statistic obtained from the deposited data, or `"not recomputable"` with the reason |
| `agrees_with_paper` | whether the recomputation reproduces the printed value, to the printed precision |
| `reanalysis` | the result at the defensible unit, with the correction from S13 applied |
| `findings` | list of `{rule, severity, observed, fix}` |
| `verdict` | `supported`, `weakened`, or `unsupported` |

A finding's `observed` field quotes what was found in the paper or computed
from the data. It never restates the rule.

### Severity

| Severity | Meaning |
|---|---|
| `blocking` | The stated evidence does not support the stated claim. A reader who trusts the text believes something the data do not show. Any S1–S16 violation. |
| `major` | A reader cannot verify the claim: an n, a family size, an interval definition, or a unit is absent, but nothing stated is actively wrong. |
| `minor` | A reporting item (R1–R7). Reported, never blocks. |

A claim's verdict is `unsupported` if any finding against it is blocking,
`weakened` if any is major, otherwise `supported`. The paper's verdict is
`blocked` if any claim is unsupported, `revise` if any is weakened, otherwise
`ship`.

### REVIEW.md sections, in order

1. **What the paper claims** — the claim set, extracted from the abstract and
   results, each with its location.
2. **What was recomputed** — what was obtained, what agreed, what did not.
   Disagreements come before agreements.
3. **Findings** — grouped by severity, each citing an `S` or `C` or `R`
   identifier, each quoting what was observed.
4. **Re-analysis** — the claims re-tested at the defensible unit and under the
   corrected family, with the figures.
5. **What survives** — the claim set with verdicts, and the sentences the
   evidence does support, written out.
6. **What could not be checked** — honestly, with the reason.

Section 5 is the deliverable. A review that lists failures without saying what
the data *do* show has not finished its job.

### Figures

A review carries **at least one figure per blocking finding**, showing the
recomputation rather than asserting it. Review figures are made by a script in
`workflows/`, follow `docs/figure-contract.md` in full, and each carries its
`.contract.json` sidecar; they are reviewed by `agents/figure-reviewer/`
before the review ships. The recurring useful ones:

- **Unit-of-analysis comparison** — the same comparison drawn at the paper's
  unit and at the defensible unit, on shared scales (`C2`), with both n stated
  (`C8`).
- **Interval reconciliation** — the interval as published beside the interval
  at the experimental unit, each named (`C10`).
- **The p-value family** — every reported p-value, before and after
  correction, with the significance threshold drawn and the claims that cross
  it labeled.
- **The claim's own data** — individual units plotted (`C9`) where the paper
  showed only a summary.

A review figure may not use a visual device the figure contract forbids, even
to make a point about the paper having used it. To show a misleading drawing,
reproduce it as a labeled inset and state in the sidecar's `claim` field what
it demonstrates.

---

## Using this file

**Authors** load `skills/statistical-review/`, which turns these rules into
procedure: how to extract the claim set from a PDF, how to reconcile a deposit
against the reported n, which recomputation each rule calls for, and which
helper runs it.

**Review** is a separate subagent, `agents/statistical-reviewer/`, with no
ability to edit files. It reaches a verdict from the paper and the deposited
data alone — the material a reader actually receives — and only then reads the
authors' analysis code, to write each fix against specific lines. A claim that
can be defended only by reading the authors' code is not reported as it should
have been, and that is itself a finding.

**The standard of proof is asymmetric, on purpose.** A finding that a claim is
unsupported must be demonstrated by recomputation from the deposited data. A
finding that a claim is *unverifiable* needs only the absence of what the rule
requires. The reviewer never asserts that a result is wrong on the strength of
a suspicion it did not test.
