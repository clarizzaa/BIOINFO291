# The figure contract

A figure is a contract between its maker and its reader. The maker promises
faithful visual comparisons, visible limits on the claim, and enough context to
interpret them. The reader brings attention to labels and scales, knowledge of
visual conventions, and questions when context is missing.

Good design makes the intended reading easy and the misleading reading
difficult.

This file states that contract as numbered rules. It is the single source for
figure standards in this repository: the generative skill
(`skills/figure-contract/`) tells an author how to satisfy these rules, and the
review subagent (`agents/figure-reviewer/`) reports which ones a finished
figure broke. Neither restates the rules; both cite these identifiers.

Source: BIOINFO291 / CHEM291, *Practical Data Analysis in Systems Biology*,
lecture 2 (data visualization).

---

## Two tiers

**Enforced rules (C1–C12).** A violation means the figure *misrepresents the
data*: a reader who trusts the drawing ends up believing something false. These
are checked on every figure and a violation blocks it.

**Legibility items (appendix).** Real problems worth fixing, but a reader who
works harder still arrives at the correct conclusion. Reported, never blocking.

The enforced rules are grouped under the five promises a figure makes.

---

## Magnitude — visual size means numerical size

### C1 — Size means value

**Promise.** The quantity a mark encodes is proportional to the mark's visual
extent, with no transformation the reader has to undo by eye.

**Fails when.** A bar axis starts anywhere but zero. A shaded region's area is
not proportional to its value. A chart is drawn in perspective or three
dimensions, so the camera angle changes the apparent comparison. Bubble
diameter or radius encodes the value, making a threefold quantity look ninefold.
A pie or donut is used for a comparison between slices.

**Check.** If the mark is a bar, area, or wedge: is the axis minimum zero, is
the rendering flat, and does doubling the value double the ink? Points and
lines are exempt from the zero baseline — see A2.

---

### C2 — Panels that are compared share their scales

**Promise.** The same height, length, or position in two panels means the same
value.

**Fails when.** Small multiples are drawn with independent axis limits, so a
small difference in one panel occupies the same space as a large one in
another. Panels are enlarged separately. A color scale is recomputed per panel
while the panels are placed side by side.

**Check.** Read the tick labels of every panel that a reader would compare. Are
the limits and the tick spacing identical? Is the color scale shared and shown
once?

---

## Meaning — every visual channel has a declared interpretation

### C3 — A line means a connection

**Promise.** Points are joined only when the order along the axis is
meaningful: time, dose, position, or another ordered variable.

**Fails when.** Independent observations are connected in file order, or
categories on a nominal axis are joined, implying a trajectory that does not
exist.

**Check.** Name the ordering the line follows. If the answer is "the order the
rows happened to be in," the marks should be points.

---

### C4 — Missing is a gap

**Promise.** A hidden mark is not an absent observation, and an absent
observation is not a zero. Observed, missing, and estimated values are visually
distinguishable.

**Fails when.** A line is drawn straight across hours that were never measured.
Missing values are substituted with zero, or dropped silently so the series
closes over the hole. Marks overlap so completely that a reader cannot tell
whether an observation is absent or merely hidden.

**Check.** Does the figure have unmeasured points? If so, is the break visible,
and does the caption say how many of the scheduled measurements were obtained?

---

### C5 — Transformations are named, and ratio axes carry their reference

**Promise.** The reader knows what scale they are looking at without reading
the methods.

**Fails when.** A log axis is labeled with the raw quantity. A fold change is
plotted without a line at the point of no change. Row-scaled or z-scored values
are shown on a color bar labeled with raw units, so identical colors stand for
measurements that differ tenfold. Zero and negative values are log-transformed
without saying how they were handled.

**Check.** Does the axis or color-bar label name the transformation? If the
quantity is a ratio, is the no-change reference drawn — 1 on a ratio scale,
0 on a log₂ scale?

---

### C6 — Color matches the structure of the variable

**Promise.** The color scale's structure mirrors the variable's structure, and
color is never the only thing carrying the meaning.

**Fails when.** A sequential quantity is drawn in rainbow, inventing visual
boundaries in a smooth field. An unordered category gets an ordered scale, or a
diverging quantity gets a scale with no defined center. The palette is
indistinguishable to a reader with common color vision deficiency. Two groups
are separated by hue alone, so the figure collapses in grayscale or for a
colorblind reader.

**Check.** Classify the variable: unordered, ordered magnitude, or diverging
around a center. Does the scale match? Is the palette colorblind-safe? Remove
color mentally — can the groups still be told apart by panel, shape, line
style, or direct label?

---

## Evidence — the reader can identify n, pairing, and uncertainty

### C7 — Plot at the experimental unit

**Promise.** The summary and the statistic describe independent units, not
repeated observations of the same unit.

**Fails when.** Cells from three cultures are shown as 36 independent points.
Cells from one patient are treated as independent replicates. Repeated
measurements of one subject are pooled as though each were a separate subject.
Any of these inflate the apparent n and shrink the error bar by a factor that
has nothing to do with the biology.

**Check.** Name the experimental unit. Count the independent units in the
figure. Does the summary — mean, interval, test, or fitted line — use that
count, or the raw row count? Sub-units may be drawn, and should be visually
subordinate to the unit-level summary.

---

### C8 — State n at that unit, per group

**Promise.** The reader can find how many independent observations each group
contributes without inferring it from the plot.

**Fails when.** n is absent. n is given for the pooled sample but not per
group. n is reported at the sub-unit level while the summary is at the unit
level, or vice versa. Groups of different size are presented as though
equivalent.

**Check.** For every group in the figure, is n printed — on the axis, in the
panel, or in the caption — and is it the count of experimental units?

---

### C9 — Small n shows every observation

**Promise.** When there are few observations, the reader sees them, not a
summary that could describe many different datasets.

**Fails when.** A bar of the mean with an error bar stands in for eight
measurements. Identical means conceal entirely different distributions. A box
plot hides bimodality. Roughly: with n ≤ 25 per group, a summary alone is
insufficient.

**Check.** Count the observations per group. If small, are the individual
points drawn — jittered, as a strip, or overlaid on the summary?

---

### C10 — Every error bar names itself

**Promise.** The interval has a stated definition, so the reader knows whether
it describes the spread of observations or the uncertainty of an estimate.

**Fails when.** An error bar appears with no definition. The same data yields
SD = 4, SE = 0.8, and a 95% CI of roughly ±1.65, and an unlabeled bar could be
any of them. A shaded ribbon's meaning is left to the reader. The interval's
n differs from the n the figure claims.

**Check.** Does the caption or legend say SD, SE, or confidence interval with
its level, together with the n it was computed from, at the experimental unit?

---

## Context — denominators, exclusions, and transformations are visible

### C11 — Exclusions and denominators are on the figure, with counts

**Promise.** The reader can see what was removed and what the proportions are
out of, and can judge whether the displayed sample still answers the question.

**Fails when.** A percentage appears without its denominator. Observations are
filtered — quality control, survival to a final timepoint, complete cases —
without the counts appearing anywhere near the figure. A pooled comparison
hides a case mix that reverses the within-group result. Different groups lose
different fractions of their observations and the figure does not say so.

**Check.** How many observations entered, and how many are displayed, per
group? Is the difference stated? If the figure shows proportions, is the
denominator visible? If filtering differs across groups, is that imbalance
disclosed on the figure rather than in the methods?

---

## Claim — the title says only what the data and design support

### C12 — The title claims only what the design supports

**Promise.** The sentence at the top of the figure is one the study design can
carry.

**Fails when.** An observational comparison is titled as an effect. A
correlation is titled as a cause. A difference is asserted without the
comparison being shown or its uncertainty being visible. The title describes a
population the sample does not represent.

**Check.** Read the title alone. What study design would be required to state
it? Is that the design that produced the data? A descriptive title — what was
measured, in whom, and what differs — is always available and always safe.

---

## Appendix — legibility items

Reported by the reviewer, never blocking.

- **A1** Every axis carries its units.
- **A2** A focused, non-zero range is legitimate for points and lines when it
  serves the question; the range should be stated in the caption and should
  retain enough context to judge the effect size.
- **A3** Direct labels beat a legend when there are few series; a legend's
  order should follow the data's order, not the alphabet.
- **A4** One comparison is annotated directly, naming the outcome and its
  units, so the reader is not left to find the point of the figure.
- **A5** Histogram and density conclusions should survive a reasonable change
  of bin width or smoothing bandwidth; a bandwidth that pushes a bounded
  variable past its bounds should be reconsidered.
- **A6** Dense scatterplots should make coincident observations countable —
  transparency, jitter, or binned counts — with the number of displayed and
  excluded points stated.
- **A7** Panels should share a consistent order, labeling, and alignment so the
  reader searches as little as possible.
- **A8** Complexity should suit the venue: exploration may be dense; a figure
  presented to an audience should introduce one comparison at a time.

---

## The sidecar

Every figure in `figures/` is accompanied by `figures/<name>.contract.json`,
written by the generating script, declaring what the figure promises. The
sidecar is what makes review mechanical: the reviewer checks the rendered image
against these declarations and reports any mismatch.

Fields marked *auto* are filled in by `save_figure`; fields marked *when it
applies* are required only in the stated case. Everything else must be
supplied by the author, with an explicit `"none"` rather than an omission — a
figure that excludes nothing should say so.

| Field | Meaning |
|---|---|
| `figure` | *auto* — file name of the image |
| `question` | the scientific question the figure answers |
| `claim` | the title's assertion, verbatim |
| `experimental_unit` | the independent unit — e.g. `chick`, `patient`, `culture` |
| `n_per_group` | object mapping group to count of experimental units |
| `n_observations` | total rows plotted when sub-units are drawn; explicit `"none"` when every mark is one experimental unit |
| `error_bar` | `none`, or a definition: `SD`, `SE`, `CI95`, with the n used |
| `transformations` | list, e.g. `["log2 of weight / day-0 weight"]`, or `[]` |
| `axes` | per axis: variable, units, limits, and whether the baseline is zero |
| `shared_scales` | *when it applies* — for any figure with more than one panel: whether compared panels share limits, and which axes |
| `color` | variable encoded, scale type, palette name, and whether color is redundant with another channel |
| `excluded` | what was filtered and how many units per group were lost |
| `missing` | how unmeasured values are represented |
| `source_script` | path to the workflow script that produced the figure |
| `config` | path to the config file it read |
| `git_sha` | *auto* — commit the figure was generated at, suffixed `-dirty` on an unclean tree |

A figure whose sidecar is absent, incomplete, or contradicted by the image
fails review regardless of how it looks.

---

## Using this file

**Authors** load `skills/figure-contract/`, which turns these rules into
procedure: which chart the question calls for, which helper enforces which
rule, and what the caption must contain.

**Review** is a separate subagent, `agents/figure-reviewer/`, with no ability
to edit files. It reaches a verdict from the image and the sidecar alone —
the material a reader actually receives — and only then reads the generating
script, to write the fix against specific lines. A figure that cannot be
judged from its image and sidecar is not self-describing, and that is itself a
finding.
