# reports — write-ups and the decision log

- `DECISIONS.md` — every consequential analytical choice, with the reason.
  Append-only; this is the scientific record the lecture asks for.
- Analysis write-ups. Every claim cites the figure or results file that
  supports it.

## Statistical reviews (week 3)

`statistical_reviews/<slug>/` holds one review per paper, in the format
`docs/statistical-review.md` specifies:

| Path | Contents |
|---|---|
| `REVIEW.md` | the review, ending with the claims the data *do* support |
| `review.json` | machine-readable findings; schema in `agents/statistical-reviewer/output_schema.json` |
| `figures/` | recomputation figures, each with its `.contract.json` sidecar |

`<slug>` is `<first-author-surname><year>-<topic>`. The recomputation tables a
review cites live in `results/statistical_reviews/<slug>/`, and the figure
verdicts in `figure_reviews/<slug>_<figure>.roundN.json`.

Reviewed so far:

| Paper | Verdict | Why |
|---|---|---|
| [`wang2026-conspecific-odors`](statistical_reviews/wang2026-conspecific-odors/REVIEW.md) | `blocked` | Every reported statistic reproduces, but the Part 2 tests were computed on 12 dog-averaged time bins rather than on the 24 dogs; no Part 2 result survives counting dogs. Part 1 holds. |
