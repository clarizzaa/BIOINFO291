# Statistical review — Wang & Horowitz 2026

**Paper.** Wang, A. & Horowitz, A. Dogs (*Canis familiaris*) distinguish
conspecific emotional chemosignals. *Scientific Reports* **16**, 11176 (2026).
[doi:10.1038/s41598-026-41426-1](https://doi.org/10.1038/s41598-026-41426-1)

**Data.** Dryad [doi:10.5061/dryad.bzkh189pt](https://doi.org/10.5061/dryad.bzkh189pt)
— `Part_1.xlsx`, `Part_2.xlsx`, `README.md`, `statistical_analyses.R`.
Registered with checksums in `data/metadata/SOURCES.md`.

**Rules.** [`docs/statistical-review.md`](../../../docs/statistical-review.md)
(S1–S16, R1–R7). Figure rules: [`docs/figure-contract.md`](../../../docs/figure-contract.md).

**Verdict: `blocked`.** Of the 11 claims in section 1: six unsupported (B1–B6), one weakened (A4), four supported (A1, A2, A3, A5).
Every reported statistic reproduces from the deposit; the failures are in what
the tests were computed on, not in the arithmetic.

---

## 1. What the paper claims

Extracted from the abstract and Results. Claim ids are used throughout.

| id | claim | where |
|---|---|---|
| **A1** | Dogs distinguish conspecific odours collected under different emotion-eliciting conditions, shown by longer investigation of novel than repeated odours | abstract; Results p. 7 |
| **A2** | Dogs distinguish joy from baseline odour | abstract; Results p. 7 |
| **A3** | Dogs distinguish joy from stress odour | abstract; Results p. 7 |
| **A4** | Dogs did *not* distinguish stress from baseline odour | Results p. 7; Discussion p. 10 |
| **A5** | There was no side bias and no difference across data-collection periods | Results p. 9 |
| **B1** | Odour condition affected the frequency of stress behaviours | Results p. 9 |
| **B2** | Odour condition affected the frequency of joy behaviours | Results p. 9 |
| **B3** | Stress odour increased proximity to the owner (the secure-base claim) | abstract; Results p. 9 |
| **B4** | Stress odour decreased proximity to a stranger | abstract; Results p. 9 |
| **B5** | Posture differed by odour condition (more upright, less prone, in blank) | Results pp. 9–10 |
| **B6** | Females responded more strongly to stress odour than males (more stress behaviours, fewer joy behaviours, closer to owner); males approached strangers more under joy odour | Results p. 10 |

---

## 2. What was recomputed

Everything the paper prints. Produced by
[`workflows/32_recompute_wang2026.py`](../../../workflows/32_recompute_wang2026.py);
tables in [`results/statistical_reviews/wang2026-conspecific-odors/`](../../../results/statistical_reviews/wang2026-conspecific-odors).

| quantity | reproduced |
|---|---|
| 16 Wilcoxon signed-rank *V* statistics (Part 1) | **16 / 16 exactly** |
| 8 omnibus statistics (Part 2: 7 Kruskal-Wallis *H*, 1 ANOVA *F*) | **8 / 8 exactly** |
| 11 Dunn post-hoc comparisons | 11 / 11, at **half** the reported p — see F6 |
| 4 sex × condition coefficients (β, SE, *t*) | **4 / 4 to 3 decimals** |
| every n printed in the paper | **all reconcile** (`n_reconciliation.csv`) |

Reproducing R's behaviour required matching two conventions that the paper does
not state: `wilcox.test` drops zero differences and switches between the exact
signed-rank distribution and a continuity-corrected normal approximation at
n = 50 or on ties; and `summary.glm` for the Gaussian family uses *t* on
residual df, not *z*. The recomputation implements both. The reported AIC values
are each exactly 2.000 below the fitted value, which is R counting the Gaussian
dispersion parameter — the models are identical.

**Nothing in this paper is miscalculated.** That is worth stating plainly
before the findings, because every finding below is about the choice of
analysis rather than its execution.

---

## 3. Findings

### Blocking

**F1 — S3, S5. The Part 2 tests count time bins, not dogs.**
*Observed.* Part 2 enrolled 24 analysed dogs in a between-subjects design
(blank 6, joy 9, stress 9). Every Part 2 comparison was computed on the
deposit's `Condition`/`Frequency` columns, which hold 12 values per condition —
the behaviour frequency averaged *across dogs* within each 5-second bin. The
authors' own `README.md` states it: "*Frequency*: Mean behavioral frequency
across all dogs for a sample point (i.e., 5-second interval)." The 24 dogs
appear only in the raw block of each sheet and are never tested. Averaging
across dogs removes between-dog variance from the denominator, and 12
consecutive bins of the same 6–9 dogs are repeated measures, not independent
observations.
*Affected.* B1, B2, B3, B4, B5, B6.
*Demonstrated.* `unit_comparison.csv`, `figures/unit_of_analysis.png`.

**F2 — S8. The reported interval is taken over time bins.**
*Observed.* Figure 6's caption reads "Data presented as means of the 12 sample
points ± S.E.M." That SEM shrinks with the number of 5-second bins, which is
fixed by the protocol at 12, rather than with the number of dogs. For proximity
to owner in the blank condition the 95% interval over 12 bins spans 0.26–0.43;
over the 6 dogs it spans 0.08–0.70 — a factor of 2.9 wider.
*Affected.* B1–B5.
*Demonstrated.* `figures/unit_of_analysis.png`.

**F3 — S13. The family of at least 39 tests is uncorrected.**
*Observed.* The Results report 39 p-values (16 Part 1 Wilcoxon, 8 Part 2
omnibus, 11 Dunn, 4 GLM). No correction is named anywhere in the methods or
results. Applying Benjamini-Hochberg across all 39 as published removes 2 of
the 33 nominally significant results; Bonferroni removes 15. 39 is a *lower*
bound: the paper also states that unreported comparisons and the per-pairing
side-bias and time-period regressions were non-significant without giving their
number, so those tests cannot be counted.
*Affected.* all claims.
*Demonstrated.* `pvalue_family.csv`, `figures/what_survives.png`.

**F4 — S12. A null result is reported as an established absence.**
*Observed.* "Subject dogs did not distinguish between stress and baseline odors
using either discrimination nor dishabituation" (Discussion), and the abstract
treats the stress/baseline null as a finding the Discussion then spends three
paragraphs explaining. The test is V = 412, p = 0.818 on 41 pairings. No
interval, no equivalence test, and no smallest effect of interest is given. The
per-dog mean difference for this pairing is compatible with effects in both
directions.
*Affected.* A4.

**F5 — S7. A normality pre-test selects the test.**
*Observed.* "The normality of the data was assessed using the Shapiro-Wilk
test. If the data were normally distributed, ANOVA with Tukey's pairwise post
hoc comparisons was used. In cases where the data deviated from normality, a
Kruskal-Wallis test with Dunn's post-hoc comparisons was used." This makes the
reported error rate conditional on a first test's outcome, and it was applied to
the 12 bin means rather than to within-group observations. In this paper the
switch produced an ANOVA for exactly one of eight outcomes (proximity to box).
*Affected.* B1–B5.
*Mitigation.* Both tests give the same qualitative answer on every outcome at
both units, so this finding changes no conclusion here. It blocks because the
procedure, not its outcome, is what the rule governs.

**F6 — S6. The Dunn p-values are one-tailed.**
*Observed.* Recomputing Dunn's test two-sided gives values exactly double the
reported ones: stranger C vs S 0.00454 (reported 0.002), upright C vs S 0.00702
(reported 0.004), prone C vs S 0.00926 (reported 0.005). R's `dunn.test` prints
a one-tailed p by default. The claims they support are stated without
directional prediction, and the omnibus tests they follow are two-sided.
*Affected.* B1–B5.
*Demonstrated.* `recompute_dunn.csv`.

### Major

**F7 — S14. Analytic freedom is conceded but not sized.**
*Observed.* "Any unreported comparisons showed no statistical significance
(p > 0.05)" concedes a larger family without saying how much larger. The
posture analysis is explicitly post-hoc — "During video analysis, distinct
postures were observed across trials, which prompted further investigation" —
and is reported at the same α as the pre-specified outcomes. No
pre-registration is cited.

**F8 — S1. The population in the claim is broader than the sample.**
*Observed.* The title and abstract claim "dogs"; the sample is 43
owner-recruited dogs tested at one laboratory, with inclusion by owner
questionnaire. Breed composition is reported (26 mixed-breed) but the sampling
frame is not described, and all odour stimuli came from a single female donor
dog — so "conspecific emotional chemosignals" rests on one conspecific.

**F9 — S2. Confounder checks are reported as null without estimates.**
*Observed.* The owner-distraction task was added partway through and testing
moved rooms between periods. Both are entered as covariates in per-pairing
linear regressions and dismissed as "no statistically significant side bias or
differences across data collection time periods (p > 0.05)". No coefficient, no
interval, and no power statement is given, on period groups of 14, 17 and 12.

**F10 — S16, C10. Figure 6's annotations and its test describe different
units.** The significance stars sit over bars of the 12 bin means and the
interval is over bins, while the claim in the text is about dogs.

### Minor

- **F11 — R2.** The direction of the Wilcoxon *V* statistic is not stated and
  flips between comparisons in the same paragraph: V = 7108 is
  habituated-minus-novel while V = 2704 is its complement (2704 + 4799 = 7503 =
  122·123/2). Both are "V" in the text.
- **F12 — R1.** 14 of 39 p-values are given only as "< 0.001".
- **F13 — R3.** No random seed is reported; none is needed for these tests, but
  the R version is given without package versions.
- **F14 — R4.** The deposited sheets paste three independent blocks side by
  side with inconsistent row counts and interleaved "`<condition> averages:`"
  rows inside the data region, which makes the file hard to read correctly; the
  `README.md` documents the columns but not the layout.

### Rules that pass

- **S4** — every n in the paper reconciles exactly against the deposit.
- **S9** — Part 1's surviving claims do not depend on the signed-rank symmetry
  assumption. The per-dog differences are right-skewed for discrimination
  (skewness 1.15), so the sign test was run beside it: 30 of 43 dogs positive,
  p = 0.014, versus signed-rank p = 0.026; dishabituation 33 of 42, p = 0.00027
  versus 0.000039. Both agree.
- **S11** — no reported p-value is below its design's resolution floor. The
  smallest order-specific comparison has 17 non-zero pairs, giving an attainable
  floor of 1.5 × 10⁻⁵, far below any reported value.
- **S10** — not applicable; no permutation or bootstrap procedure is used.
- **S15** — the abstract's Part 1 sentences match the tests that support them.

---

## 4. Re-analysis

Two changes, applied together: Part 2 tested on dogs rather than bins, and
Benjamini-Hochberg applied across all 39 reported tests.

![Unit of analysis](unit_of_analysis.png)

**Part 2, per outcome** (`unit_comparison.csv`):

| outcome | p on 12 bins | p on 6/9/9 dogs |
|---|---|---|
| stress behaviours | 0.000028 | 0.106 |
| joy behaviours | 0.0000062 | 0.038 |
| proximity to owner | 0.0000096 | 0.231 |
| proximity to stranger | 0.016 | 0.437 |
| upright posture | 0.00022 | 0.116 |
| prone posture | 0.00040 | 0.179 |
| proximity to box | 0.367 | 0.869 |
| sitting posture | 0.079 | 0.572 |

Six of eight were reported as significant; one survives the change of unit, at
p = 0.038 among 39 tests.

The four sex × condition coefficients, refit on the 24 dogs, give p = 0.18,
0.38, 0.42 and 0.48 (`recompute_glm.csv`). With 4 female and 5 male dogs in the
stress condition, an interaction of the claimed size is not estimable from these
data.

![What survives](what_survives.png)

**Part 1** was also re-tested at the dog level, by averaging each dog's two or
three odour pairings to one value and testing that against zero
(`part1_dog_level.csv`). It holds: discrimination V = 657 on 43 dogs,
p = 0.026 (pooled 0.0075); dishabituation V = 781 on 42 dogs, p = 0.000039
(pooled 0.00010). Median per-dog difference +0.62 s and +1.17 s respectively.
The pooling inflated the significance of the discrimination result but did not
create it.

---

## 5. What survives

**Supported.**

- **A1, A2, A3.** Dogs investigated a novel conspecific odour longer than a
  repeated one, and this holds for joy versus baseline and for joy versus
  stress. It survives correction across all 39 tests, re-testing at the dog
  level, and the sign test. The defensible sentence: *in 43 owner-recruited
  dogs, investigation time was longer for a novel conspecific odour than for the
  repeated one (median per-dog difference +0.62 s for the simultaneous
  comparison, +1.17 s against the third presentation), and the joy–baseline and
  joy–stress pairings each showed this individually.*
- **A5.** No side bias or period effect was detected — reported as such, with
  F9's caveat that "not detected" is all the check establishes.
- The *descriptive* content of B1–B5: dogs behaved differently in the blank
  condition from the two odour conditions. The direction and the pattern across
  bins are in the data; what is not established is that the difference exceeds
  what 6 to 9 dogs per group can distinguish from noise.

**Weakened.** A4 — a non-rejection reported as an established absence (F4).
The estimate and its interval are what the claim needs, and neither is given.

**Unsupported as stated.** B1–B6 — the inferential claims that odour condition
*affected* each behaviour, and the sex × condition claim. None survives counting
dogs. B3, the secure-base result the abstract leads with and the Discussion
builds on, moves from p = 9.6 × 10⁻⁶ to p = 0.23. B6 carries a blocking S3
finding like the rest, so it is unsupported rather than merely weakened: the
sex difference is a hypothesis these data cannot test, not a finding.

**One honest caveat about the re-analysis.** The claim "0 of 23 Part 2 tests
survive" rests on a nearest value of q = 0.0505 against a 0.05 threshold. That
is a coin-flip distance from the threshold and is labelled as such on the
figure. The robust statement is not "exactly zero survive" but "no Part 2
result remains clearly significant, and the strongest sits on the threshold".

---

## 6. What could not be checked

- **The behavioural coding itself.** The deposit contains coded frequencies,
  not the videos. Inter-observer reliability is not reported and cannot be
  assessed (the coder was blind to condition, which is stated).
- **Per-group entry counts for Part 2.** The paper reports 2 dogs excluded for
  not investigating the odour but does not say which conditions they were
  assigned to, so the per-condition denominators before exclusion are not
  recoverable (S11/C11).
- **The size of the undeclared test family** (F3, F7). The side-bias and
  period regressions are described but their p-values are not reported, so they
  cannot be counted or corrected.
- **Whether the odour stimuli differed chemically.** No chemical
  characterisation is reported; the emotional validity of the stimuli rests on
  the induction protocol alone. This is a design question, not a statistical
  one, and is noted rather than scored.

---

## Provenance

| | |
|---|---|
| recomputation | `workflows/32_recompute_wang2026.py` |
| figures | `workflows/33_fig_wang2026.py`, each with a `.contract.json` sidecar |
| tables | `results/statistical_reviews/wang2026-conspecific-odors/` (9 CSVs) |
| environment | `environment/env-stats.yml`, `env-stats.lock.txt` |
| figure review | `reports/figure_reviews/wang2026_*.json` |
