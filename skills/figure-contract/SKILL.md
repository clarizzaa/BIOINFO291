---
name: figure-contract
description: "Make a matplotlib figure that keeps its contract with the reader, for any tabular measurement data. Load before producing any figure that will be saved, shown, or handed in. Covers stack conventions (fig/ax rather than pyplot state, Agg, saving through save_figure), choosing the chart from the question, communicating the finding (one comparison per figure, a descriptive result-bearing title, direct labels, meaningful group order), and twelve enforced rules: proportional ink, shared scales across compared panels, missing drawn as a gap, plotting at the experimental unit rather than pseudo-replicates, stated n per group, named error bars (SD vs SE vs CI), visible exclusions and denominators, honest titles. Ships kernel.py helpers (contract_style, unit_level, interval, line_with_gaps, trajectories_by_group, strip_with_units, annotate_n, check_palette, save_figure) plus a mandatory sidecar declaring what each figure promises, so review can be mechanical. Not for throwaway exploratory plots."
---

# Making a figure that keeps its contract

A figure is a contract between its maker and its reader. The rules are in
**`docs/figure-contract.md`** — twelve enforced (C1–C12) and an appendix of
legibility items (A1–A8). This skill does not restate them; it turns them into
procedure. Read the rule when a check below cites it.

`kernel.py` loads automatically with this skill. Its functions exist so that
obeying a rule is less work than breaking one.

Nothing here is specific to one dataset or one project. The rules apply to any
tabular measurement data; substitute your own columns.

---

## The stack

**matplotlib**, on pandas. No seaborn, no plotly: the rules below are stated as
operations on axes and artists, and a layer that chooses for you makes some of
them unreachable.

Three conventions, because they decide whether a figure is reproducible:

- **Always `fig, ax = plt.subplots(...)`, then draw on `ax`.** Never the pyplot
  state machine (`plt.plot`, `plt.title`). A script that mutates global state
  produces a different figure depending on what ran before it.
- **Always `fig.savefig(...)`** — or rather, always `save_figure(fig, ...)`,
  which calls it and writes the sidecar. Never `plt.savefig`.
- **Set `matplotlib.use("Agg")` before importing pyplot** in any script, so the
  figure renders identically with no display attached.

Call `contract_style()` once at the top. It sets a small styling floor — font
ladder, outward ticks, no top/right spines, unframed legends, 300 dpi — and
nothing else. It is deliberately thin: this skill governs what a figure
promises, not what it looks like.

---

## The procedure

1. **State the question in one sentence.** Not "plot the data" — the actual
   comparison you want a reader to make. It goes in the sidecar verbatim.
2. **Name the experimental unit before you touch the plotting code** (C7).
   Patients, cultures, animals, plots, runs — the thing that was independently
   assigned or sampled. Repeated measurements of one unit are not replicates.
   Count the units per group now; that count is your n (C8).
3. **Choose the chart from the question**, using the table below.
4. **Draw it with the helpers**, which carry the rules.
5. **Declare and save with `save_figure`.** It refuses to write a PNG whose
   sidecar is incomplete, so a figure cannot exist here without saying what it
   promises.

Then hand the figure to the `figure-reviewer` subagent. It sees only the image
and the sidecar at first — the material a reader actually receives.

---

## Choosing the chart

| The question is | Draw | Watch |
|---|---|---|
| How many in each group? | bars from zero, or a dot plot | C1 |
| What fraction? | bars or a stacked bar with the denominator stated | C1, C11 |
| How does it change over an ordered variable? | lines, one per unit, grouped into panels | C2, C3, C4 |
| How do a few groups compare on one measure? | every unit as a point, with a named interval | C9, C10 |
| How are two continuous variables related? | scatter; bin or make transparent when dense | A6 |
| How is one variable distributed? | histogram or strip; check the conclusion survives the bin width | A5 |
| Is the change within subjects? | paired lines or the differences themselves | C7 |
| Ratio or fold change? | log scale with the reference line drawn | C5 |

Two defaults worth stating: **small multiples beat a crowded legend** once
there are more than about five series, and **a comparison of groups almost
always wants the individual units visible**, not just a summary.

---

## Which helper carries which rule

| Rule | Helper | What it does |
|---|---|---|
| C1 size means value | — | your choice; bars get `ax.set_ylim(bottom=0)` |
| C2 shared scales | `trajectories_by_group` | panels built with `sharex=sharey=True`, so the rule cannot be lost by forgetting |
| C3 lines mean connection | — | only join points along an ordered variable |
| C4 missing is a gap | `line_with_gaps` | keeps NaN rather than dropping it, so the line breaks |
| C5 transformations named | `contract_caption` | emits the transformation text from the sidecar |
| C6 colour matches structure | `OKABE_ITO`, `SEQUENTIAL`, `DIVERGING`, `check_palette` | colourblind-safe defaults; `check_palette` raises on rainbow scales |
| C7 experimental unit | `unit_level` | collapses repeated measurements to one row per unit before any summary |
| C8 state n per group | `annotate_n`, `contract_caption` | prints n above each group and into the caption |
| C9 small n shows all | `strip_with_units`, `trajectories_by_group` | draws every unit; summary sits on top |
| C10 error bars named | `interval`, `interval_name` | returns the defining words with the number, never a bare bar |
| C11 exclusions visible | `contract_caption` | emits the `excluded` and `missing` clauses |
| C12 honest title | — | judgement; see below |

`contract_style()` sets a small styling floor — sizes, tick direction, 300 dpi,
unframed legends. It is deliberately thin. This skill governs what a figure
*promises*, not how it looks, and the floor lives here rather than in an
external dependency so a clean checkout reproduces every figure.

---

## Writing the title (C12)

Write the descriptive version first: **what was measured, in whom, and what
differs.** Then ask what study design would license anything stronger. If the
data are observational, the comparison is between groups that were not
randomised, or the outcome was measured once, stop at descriptive.

- "Treatment B improves recovery" — a causal claim; needs randomisation, and
  says nothing about how much or in how many.
- "Group B subjects recovered fastest, median 12 days (n = 10)" — says what
  happened, in what unit, with how many.

If the figure's single most important comparison isn't annotated on the figure
itself, add it (A4): name the outcome, the units, and the groups compared.

---

## The caption

Build the required clauses with `contract_caption(contract)` and prepend your
own descriptive sentence. The caption must carry, at minimum:

- n, at the experimental unit, per group (C8)
- what every interval or band is (C10)
- any transformation (C5)
- what was excluded and how many units per group were lost (C11)
- how unmeasured values are drawn (C4)

---

## Communicating the finding

Keeping the rules stops a figure misleading. It does not make the figure say
anything. These are the moves that do.

**One figure, one comparison.** A reader takes one idea from a figure. Decide
which, before drawing. Everything that does not serve it is competing with it.

**Put the finding in the title, descriptively.** A title that names the
variable ("Weight by treatment group") wastes the most-read line in the figure
on something the axes already say. A title that states what was found
("Group B subjects were heaviest at the final visit, median 281 g") spends it
on the result. Stay descriptive: what was measured, in whom, and what differs
(C12).

**Annotate the comparison you want read.** Name the outcome, its units, and the
groups compared, on the figure (A4). A reader should not have to reconstruct
your point from the axes.

**Order groups by something meaningful** — by the outcome, by dose, by time —
unless the categories have a conventional order. Alphabetical is almost never
the order the question implies.

**Label series directly** rather than through a legend when there are only a
few (A3). A legend costs the reader a saccade and a working-memory slot per
series; a label at the end of the line costs nothing.

**Let exploration be dense and presentation be sparse.** The figure you use to
understand the data and the figure you use to show a result are rarely the
same figure. Build both; ship the second.

---

## Worked example

Generic on purpose — substitute your own column names. A repeated-measures
dataset: `subject` measured at several `visit`s, assigned to a `treatment`.
The unit is the subject, and the comparison is restricted to the final visit.

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

contract_style()
df = pd.read_csv(cfg["dataset"]["path"])
unit, group, value, time = (cfg["dataset"][k] for k in
                            ("experimental_unit", "group", "value", "time"))

# C7: collapse repeated measurements to one row per subject BEFORE summarising.
final = unit_level(df, unit=unit, group=group, value=value, how="last", time=time)

# C11: restricting to a timepoint is a filter. Count what it removed, per group
# — unequal loss between the groups being compared is the thing to surface.
last_visit = cfg["dataset"]["final_visit"]
kept = final[final[time] == last_visit]
lost = (final.groupby(group).size() - kept.groupby(group).size()).to_dict()

fig, ax = plt.subplots(figsize=cfg["figure"]["size_single_panel"],
                       constrained_layout=True)
n_per_group, eb = strip_with_units(ax, kept, group=group, value=value,
                                   unit=unit, kind=cfg["contract"]["interval"])
annotate_n(ax, n_per_group, unit=unit)
ax.set_xlabel("Treatment group")
ax.set_ylabel(f"Outcome at final visit ({cfg['dataset']['value_units']})")
ax.set_title("Outcome at the final visit, among subjects reaching it")

save_figure(fig, "figures/final_outcome.png", {
    "question": "Does the outcome at the final visit differ between groups?",
    "claim": ax.get_title(),
    "experimental_unit": unit,
    "n_per_group": n_per_group,
    "n_observations": "none; every point is one subject",
    "error_bar": f"{eb}, per group",
    "transformations": [],
    "axes": {"y": {"variable": value, "units": cfg["dataset"]["value_units"],
                   "baseline_zero": False}},
    "color": {"variable": group, "scale": "qualitative", "palette": "okabe_ito",
              "redundant_with": "x position"},
    "excluded": f"subjects not reaching the final visit, by group: {lost}",
    "missing": "none in the displayed subset",
    "source_script": "workflows/NN_fig_final_outcome.py",
    "config": "configs/<dataset>.yaml",
})
```

Three things in that example are the general pattern, not incidental detail:
`unit_level` is called before any summary; the filter's per-group cost is
computed rather than described; and both end up in the sidecar *and* on the
figure, because a reader who sees only the image must still be able to tell
that the groups were filtered unequally.

---

## What blocks a figure

Any violation of C1–C12. Most common, in order:

1. **n is the row count, not the unit count** (C7, C8). The single most
   frequent serious error. Call `unit_level` before any summary.
2. **An unlabelled error bar** (C10). The same data gives SD, SE, and CI that
   differ by a factor of five.
3. **A filter with no count** (C11). "Complete cases" and "survivors" are
   filters.
4. **A title the design cannot support** (C12).

---

## In this repository

Everything above is general. These are the local conventions it assumes, and
the only part to change if you reuse this skill elsewhere.

- The rules live in `docs/figure-contract.md`; the reviewer is
  `agents/figure-reviewer/`. Both cite the same identifiers.
- Every figure is produced by a numbered script in `workflows/`, never by hand
  and never in an untracked notebook (WORKSPACE.md rule 8).
- Thresholds — the n below which every observation must be shown, figure sizes,
  dpi, palette — are config values in `configs/<dataset>.yaml`, read via
  `src/config.py`, not literals in the script (WORKSPACE.md rule 3).
- Import the helpers with `from figure_contract import ...` after putting
  `src/` on the path; that module re-exports this `kernel.py`, so workflow
  scripts do not depend on the skill harness and a clean checkout still
  regenerates every figure.
- `src/plotting.py` is a different thing — week 1's fixed entity colours for
  the melanoma analysis. Call one style function or the other, not both.
- A pytest check enforces that every PNG in `figures/` has a complete sidecar.
