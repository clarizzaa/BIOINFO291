# Decision log

Append-only record of consequential analytical and structural choices.
Format is defined in [WORKSPACE.md](../WORKSPACE.md) section 4.

## 2026-10-07  Repository structure
Decision:     Adopt the course reference layout (data/{raw,metadata,processed},
              src, workflows, configs, results, figures, reports, tests,
              environment), with a README in every directory.
Alternatives: A flat repo with notebooks; the layout of the earlier
              `pda-course` repo.
Reason:       The separation of immutable inputs from regenerable outputs is
              what makes "rerun from scratch" checkable rather than aspirational.
              Per-directory READMEs mean the structure explains itself to a
              reader who has not seen the chat.
Affects:      whole repository

## 2026-10-07  Raw and processed data excluded from git
Decision:     Track provenance (`data/metadata/SOURCES.md`: URL/accession,
              date, SHA-256) instead of committing data files.
Alternatives: Commit raw data directly; use git-lfs.
Reason:       Single-cell matrices are too large for a git repository, and a
              checksum plus a stable accession reproduces the input exactly.
              git-lfs adds a dependency the grader would also need.
Affects:      .gitignore, data/metadata/SOURCES.md

## 2026-10-08  Signature performance is cross-validated, and benchmarked
Decision:     Derive the responder signature from per-patient CD8 pseudobulk
              and report leave-one-out cross-validated AUC as the headline
              number, with the in-sample AUC and an independently published
              signature shown alongside. Exclude ribosomal, mitochondrial,
              pseudogene and housekeeping families from signature membership.
Alternatives: Reporting the in-sample AUC, which is what ranking genes on all
              samples and scoring those same samples produces.
Reason:       Choosing the most different genes on a set of samples and then
              scoring those samples measures fit, not generalisation. Within
              each fold the signature is re-derived on the other patients
              only, so the held-out score is honest. The gap is real but
              moderate: 0.96 in-sample versus 0.88 cross-validated at patient
              level (0.91 versus 0.84 at biopsy level). The published
              Sade-Feldman signature, which never saw this analysis, reaches
              0.89 at patient level, which corroborates the biology rather
              than the fitting procedure.
              Excluded gene families track library composition and cell size
              rather than T-cell state, and would otherwise dominate a
              difference-of-means ranking.
Note:         No single gene survives BH correction across 41,744 genes at
              patient level (minimum padj 0.122) although the rank test's
              floor at n = 10 vs 18 is 1.5e-7, so this is a real absence of
              single-gene signal rather than a resolution limit. The
              aggregate score still separates the groups at AUC 0.88 (25 genes
              per direction, re-derived within each fold; the fixed signature
              reported here is 20 per direction): the response signal is
              distributed across many genes, not concentrated in any one.
Affects:      configs/scrnaseq.yaml (pseudobulk_de.*, benchmark_signature.*),
              workflows/06_pseudobulk_de.py, results/signature_auc.csv,
              results/signature_genes.json, figures/signature_auc.png

## 2026-10-08  The patient is the experimental unit, not the biopsy
Decision:     Test composition on per-patient mean proportions (n = 28), and
              report the biopsy-level test (n = 48) beside it. Exclude the
              four patients whose own biopsies carry contradictory response
              labels from the patient-level response test only. Compare Post
              against Pre with a paired signed-rank test on the 11 patients
              biopsied at both timepoints.
Alternatives: Biopsy-level Mann-Whitney on all 48, as the reference example
              does; a mixed-effects model on all 48 with a patient random
              intercept.
Reason:       The 48 biopsies come from 32 patients, so they are not 48
              independent replicates, and WORKSPACE.md section 3 requires the
              unit to be the patient. Response in GSE120575 is recorded per
              lesion, which is why P1, P4, P5 and P28 are internally
              contradictory; no patient-level label exists for them. A
              mixed-effects model would retain all 48 points but is fragile at
              this n and harder to defend than a rank test.
              The correction changes the conclusions, which is the point of
              reporting both. Surviving at patient level: cycling T up in
              non-responders (padj 0.0005), B cells up in responders (0.012),
              pDC up in non-responders (0.042). Not surviving: macrophage /
              monocyte (biopsy 0.019 -> patient 0.305) and the CD8
              memory-to-exhausted ratio (biopsy 0.035 -> patient 0.144). CD8
              exhausted sits on the boundary (0.026 -> 0.051). Those three
              were carried by repeated biopsies of the same patients.
              A sensitivity analysis excluding the FACS-enriched biopsies
              (n = 24 patients) leaves the three surviving findings intact.
Affects:      configs/scrnaseq.yaml (composition.*), workflows/05_composition.py,
              results/composition_stats.csv, results/patient_proportions.csv,
              figures/composition_boxplots.png

## 2026-10-08  Hierarchical cluster annotation, calibrated within each level
Decision:     Label clusters (not cells) in three levels - compartment, then
              subset within the T compartment, then CD8 state - z-scoring each
              marker panel only across the clusters still in contention at
              that level. NK is a level-1 compartment defined by KLRF1, KLRD1
              and NCAM1.
Alternatives: A single flat argmax over nine lineage panels, as first
              implemented and as the reference example does; per-cell gene-set
              scoring with `sc.tl.score_genes`.
Reason:       The flat version was tried and was wrong in three ways, each
              traceable to comparing panels standardised over all 28 clusters.
              (1) Clusters 5 and 11 were called NK on NKG7 and GNLY, which are
              cytotoxicity genes shared with effector CD8 T cells; both have
              CD3D ~7.3 and KLRF1 <0.25 and are T cells. (2) The true NK
              cluster was lost: NK cells are CD3-negative, so a combined
              "T/NK" compartment keyed on CD3 excluded it and it fell through
              as Unassigned. (3) The CD8 memory/exhausted split came out 1
              versus 8 because the two state panels sit on different baselines
              when standardised across every cluster, including B and myeloid.
              Calibrating within the contested set fixes all three and leaves
              no cluster unassigned.
              CD8 states are assigned per cluster rather than per cell: the
              memory-exhaustion axis is a continuum, and a per-cell cut places
              a hard boundary in the middle of it that the graph does not
              support.
Caveat:       CD4 mRNA is captured poorly relative to CD8A, so the CD4/CD8
              boundary rests on relative, not absolute, panel scores. CD4
              T conv is the largest population (34.6%) and may absorb some
              weakly-labelled CD8 cells.
Affects:      configs/scrnaseq.yaml (annotation.*), workflows/04_annotate.py,
              results/cluster_annotation.csv, figures/umap_celltypes.png,
              figures/marker_heatmap.png, figures/marker_dotplot.png

## 2026-10-08  QC thresholds, and mitochondrial content computed in TPM space
Decision:     Remove cells with >=40% mitochondrial TPM and genes detected in
              fewer than 3 cells. Do not apply a minimum-genes-per-cell
              filter. Compute mitochondrial fraction after converting the
              matrix back to linear TPM (2**x - 1), not on the log values.
Alternatives: The common defaults of 5-20% mitochondrial content and
              `min_genes=200`; using `sc.pp.calculate_qc_metrics` directly.
Reason:       The authors released an already-curated CD45+ set with their own
              per-cell quality filters applied, so the observed minimum is
              ~1,000 genes per cell and a 200-gene floor removes nothing; it
              is reported in the QC figure for inspection instead. A 5%
              mitochondrial cutoff is tuned to droplet data and would discard
              most of a Smart-seq2 experiment, whose median here is 12.7%.
              Scanpy's default metrics assume raw counts; a percentage taken
              over log2(TPM+1) values is not a fraction of transcripts, so the
              values are de-logged first.
              Result: 231 cells removed (16,291 -> 16,060) and 10,045 genes
              removed (55,737 -> 45,692), matching the reference example.
              Loss is marginally uneven across groups (1.6% of non-responder
              vs 1.1% of responder cells, Fisher p = 0.005), which is stated
              on the figure rather than described as balanced.
Affects:      configs/scrnaseq.yaml (qc.*), workflows/02_qc.py,
              results/qc_counts.csv, figures/qc_metrics.png

## 2026-10-08  FACS sorting fraction recovered and kept as a covariate
Decision:     Parse the second header row of the TPM matrix and record a
              `sort_fraction` column (`unsorted`, `T_enriched`,
              `myeloid_enriched`) on every cell, rather than taking biopsy
              labels from the annotation file alone.
Alternatives: Use the annotation file only, as the reference example does;
              or drop the 991 cells from sorted fractions outright.
Reason:       The two released files disagree for 991 cells. The expression
              matrix records that nine Post biopsies were FACS-sorted into
              T-cell- or myeloid-enriched fractions; the annotation file
              collapses that away. Cell-type proportions within a sorted
              fraction reflect the sorting gate, not the tumour, so this is a
              direct confounder of the central composition comparison, and it
              is not balanced across groups: myeloid-enriched fractions occur
              only in responders (2 biopsies, 118 cells) while T-enriched
              fractions are mostly non-responders (5 vs 2 biopsies).
              Discarding the cells would lose data and still leave the
              imbalance unexamined; keeping the label permits an explicit
              confounding check and a sensitivity analysis.
Affects:      workflows/01_build_anndata.py, workflows/05_composition.py,
              results/cohort_summary.csv, results/confounding_check.csv

## 2026-10-07  One rules file, several entry points
Decision:     WORKSPACE.md holds the rules; AGENTS.md and CLAUDE.md point to
              it; the Claude Science project-context text also points to it and
              is recorded in docs/claude-science-setup.md.
Alternatives: Duplicate the rules into each harness-specific file.
Reason:       Claude Science supports neither CLAUDE.md nor a rules folder, so
              the rules must be injected through project settings. Duplicating
              them guarantees drift; a pointer does not.
Affects:      WORKSPACE.md, AGENTS.md, CLAUDE.md, docs/claude-science-setup.md

## 2026-10-08  Figure standards as one numbered rule document, in two tiers
Decision:     Write the lecture-2 visualization principles as numbered rules in
              `docs/figure-contract.md`, split into twelve enforced rules
              (C1-C12) and a legibility appendix (A1-A8). Both the generative
              skill and the review subagent cite these identifiers rather than
              restating the rules.
Alternatives: A single flat list of ~23 equally weighted rules; prose guidance
              with no identifiers.
Reason:       Same argument as WORKSPACE.md: rules stated in two places drift.
              The two tiers exist because an agent holding equally weighted
              rules reports "axis missing units" at the same volume as "n is
              the row count, not the unit count"; review then reads as lint and
              stops being read. An enforced rule is one whose violation makes a
              reader believe something false.
Affects:      docs/figure-contract.md, skills/figure-contract/,
              agents/figure-reviewer/

## 2026-10-08  Generation and review are separate agents
Decision:     The generative half is a skill (`skills/figure-contract/`); the
              review half is a distinct agent profile
              (`agents/figure-reviewer/`, FIGURE_REVIEWER) that reports and
              does not edit.
Alternatives: One skill containing both a how-to and a self-check section.
Reason:       A self-check performed by the author of a figure is performed by
              something that already knows what the figure meant; the contract
              is owed to a reader who does not. A reviewer that can silently
              fix a problem also leaves no record that the problem existed, so
              the review loop becomes unauditable.
Limitation:   The no-editing rule is enforced by the profile's system prompt,
              not by the harness: the Claude Science profile API exposes a
              per-tool blocklist only for connector tools, so core tools such
              as `edit_file` cannot be withheld. Recorded in
              docs/claude-science-setup.md, known gaps.
Affects:      agents/figure-reviewer/, docs/claude-science-setup.md

## 2026-10-08  Every figure carries a machine-readable sidecar
Decision:     Each figure writes `figures/<name>.contract.json` declaring the
              question, claim, experimental unit, n per unit, error-bar
              definition, transformations, axes, colour mapping, exclusions,
              missing-value treatment, source script, config and git SHA.
              `save_figure()` refuses to write a PNG whose declaration is
              incomplete, and a pytest check enforces the same at the repo
              level.
Alternatives: Review the image alone; keep the same information in the figure
              caption only.
Reason:       Review of an image alone is a matter of opinion about what the
              figure "looks like it is claiming". A declaration makes the check
              mechanical: the reviewer compares the drawing against what the
              figure says about itself, and a false declaration is a finding in
              its own right. Making `save_figure` the only sanctioned save path
              means a figure cannot exist in this repository without one.
Affects:      skills/figure-contract/kernel.py, docs/figure-contract.md,
              figures/, tests/

## 2026-10-08  Review is two-pass; the script cannot rescue the figure
Decision:     The reviewer reaches a verdict from the rendered image and the
              sidecar alone, writes it down, and only then reads the generating
              script - solely to make each fix specific to a line.
Alternatives: Give the reviewer everything at once; or withhold the script
              entirely.
Reason:       The image and sidecar are what a reader actually receives, so a
              verdict formed from them tests the thing that matters. Withholding
              the script entirely would make the feedback vague. Allowing the
              script to change the verdict would let a figure be defended by
              material the reader never sees; a figure that needs its source
              code to be understood is not self-describing, which is itself
              worth reporting.
Affects:      agents/figure-reviewer/AGENT.md

## 2026-10-08  The styling floor is in the repository, not a platform skill
Decision:     `skills/figure-contract/kernel.py` carries its own small rcParams
              block (`contract_style`) rather than depending on the
              platform-provided `figure-style` skill.
Alternatives: Call the platform skill's `apply_figure_style()` and keep this
              skill purely about the contract.
Reason:       WORKSPACE.md requires that a stranger with this repository can
              reproduce every figure. A script that calls a function living in
              a web-configured platform skill does not regenerate on a clean
              checkout. The styling floor is deliberately thin so the skill
              remains mostly lecture principles.
Affects:      skills/figure-contract/kernel.py, skills/figure-contract/SKILL.md

## 2026-10-08  ChickWeight for week 2; the chick is the experimental unit
Decision:     Use `datasets::ChickWeight` (578 measurements, 50 chicks, diets of
              20/10/10/10) for the week-2 figures, exported with provenance by
              `workflows/20_get_chickweight.R`. The experimental unit is the
              chick; repeated measurements of one chick are not replicates.
Alternatives: The week-1 melanoma data (analysis not yet complete); Palmer
              Penguins (no repeated measures, no attrition).
Reason:       The dataset exercises nine of the twelve enforced rules without
              contrivance. In particular the attrition is not random across
              groups - five chicks never reach day 21, four of them on diet 1
              and one on diet 4, none on diets 2 or 3 - so restricting to the
              final measurement silently drops a fifth of diet 1 and nothing
              from two other diets. That makes C11 a real finding rather than a
              teaching exercise.
Affects:      configs/chickweight.yaml, workflows/2*, data/raw/chickweight.csv,
              data/metadata/chickweight_provenance.txt

## 2026-10-08  The "show every observation" threshold is a config value
Decision:     C9's threshold lives in `configs/chickweight.yaml` as
              `contract.show_all_observations_below_n: 25`, not as a number in
              the rule text or in a script.
Alternatives: State a fixed number in docs/figure-contract.md; leave it to the
              reviewer's judgement.
Reason:       WORKSPACE.md rule 3 says code reads the number and code does not
              contain it; a threshold buried in prose is the same violation one
              layer up. A declared parameter is also one the reviewer can check
              a figure against.
Affects:      configs/chickweight.yaml, docs/figure-contract.md

## 2026-10-15  Statistical review is a contract, a skill, and a non-editing agent
Decision:     Week 3 mirrors the week-2 structure exactly. The rules live in
              `docs/statistical-review.md` as sixteen enforced rules (S1-S16)
              plus seven reporting items (R1-R7); the procedure for running a
              review lives in `skills/statistical-review/`; the verdict is
              reached by a separate subagent, `agents/statistical-reviewer/`,
              that cannot edit files. Neither the skill nor the agent restates
              a rule; both cite its identifier.
Alternatives: One skill that both runs and judges the review; a single prose
              rubric with no machine-readable findings.
Reason:       The same argument as the figure contract. The author of an
              analysis knows what they meant and the reviewer must not; a
              reviewer that can quietly fix a problem leaves no record that the
              problem existed. Keeping the rules in one numbered document is
              what lets a finding be cited rather than argued.
Affects:      docs/statistical-review.md, configs/statreview.yaml,
              skills/statistical-review/, agents/statistical-reviewer/

## 2026-10-15  A blocking finding must be demonstrated by recomputation
Decision:     The standard of proof in `docs/statistical-review.md` is
              deliberately asymmetric: a claim is reported as *unsupported*
              only when recomputation from the deposited data shows it, while a
              claim is reported as *unverifiable* on the absence of what a rule
              requires. A paper whose data cannot be obtained is not reviewed.
Alternatives: Allow blocking findings from the text alone, so any paper could
              be reviewed; review from the PDF and label the uncertainty.
Reason:       The assignment's input is the paper *and* its data, and a review
              that asserts a result is wrong without testing it is the same
              error it is auditing. This also makes data availability a gating
              check in `configs/statreview.yaml` rather than an afterthought.
Affects:      docs/statistical-review.md, configs/statreview.yaml,
              workflows/30_fetch_papers.py

## 2026-10-15  Wang & Horowitz 2026 as the reference review
Decision:     The first review is Wang & Horowitz, *Scientific Reports*
              16:11176 (2026), "Dogs distinguish conspecific emotional
              chemosignals", with the Dryad deposit doi:10.5061/dryad.bzkh189pt.
Alternatives: The other four cat/dog papers suggested in lecture 3.
Reason:       The deposit includes the authors' own analysis script, so the
              two-pass protocol can actually be exercised: a verdict from the
              paper and data, then the script for remediation. The paper also
              exercises the unit rules without contrivance - Part 2 enrolled 24
              analyzed dogs (9 joy, 9 stress, 6 blank) but its condition
              comparisons were run on 12 per-condition sample-point means, with
              the dogs averaged away and the time bins treated as independent.
Affects:      configs/statreview.yaml, workflows/30_*, workflows/31_*,
              reports/statistical_reviews/wang2026-conspecific-odors/

## 2026-10-15  Dryad will not serve this deposit to an automated client
Decision:     `workflows/30_fetch_papers.py` resolves the Dryad file list over
              the API but the file bytes are placed in `data/raw/papers/<slug>/`
              by hand. The checksums in `data/metadata/SOURCES.md` are what
              pins the files, not the download.
Alternatives: Spoof a browser user-agent and session to defeat the block.
Reason:       Dryad's API download route returns 401 ("must have current bearer
              token") and its `/downloads/file_stream/` route returns 403 to
              non-browser clients, while the dataset landing page is public.
              Defeating a site's bot protection is not a reproducibility
              strategy, and a recorded SHA-256 makes a hand-placed file exactly
              as verifiable as a downloaded one.
Affects:      workflows/30_fetch_papers.py, data/metadata/SOURCES.md

## 2026-10-15  Review figures go through FIGURE_REVIEWER before a review ships
Decision:     `docs/statistical-review.md` requires each review figure to pass
              `agents/figure-reviewer/` before the review is published. Round-1
              verdicts are kept in `reports/figure_reviews/<slug>_<figure>.roundN.json`
              alongside the week-2 ChickWeight verdicts.
Alternatives: Trust the author of the review to apply the figure contract to
              their own figures, since they wrote the statistical contract too.
Reason:       The first render of both Wang & Horowitz figures was blocked, and
              one finding was substantive rather than cosmetic: the headline of
              `unit_of_analysis.png` stated the p-value change in the opposite
              direction to the one the panels showed. The author of a figure
              knows what they meant; that is precisely why they are the wrong
              reader to check it. A reviewer that also wrote the rules it is
              checking is not an independent check.
Affects:      docs/statistical-review.md, workflows/33_fig_wang2026.py,
              reports/figure_reviews/wang2026_*.json

## 2026-10-15  Every recomputation table carries a stable test_id
Decision:     Each row of every table written by `workflows/32_recompute_wang2026.py`
              carries a `test_id` (e.g. `p2.omnibus.owner`), and downstream steps
              join on it rather than on a human-readable label.
Alternatives: Join on the outcome name and test as printed.
Reason:       The first draft of `what_survives.png` joined two tables on their
              label columns. The labels were written differently in each
              ("owner" versus "owner (Kruskal-Wallis)"), the inner join silently
              dropped 12 of the 39 tests, and the figure's sidecar declared 11
              Part 2 tests where there were 23 - while the title still claimed a
              correction over 39. A silent row drop in a figure about
              multiple-testing corrections is the exact failure the figure was
              drawn to expose.
Affects:      workflows/32_recompute_wang2026.py, workflows/33_fig_wang2026.py,
              skills/statistical-review/kernel.py (collect_family raises on a
              missing or duplicate id)

## 2026-10-15  Review numbers are produced by a workflow step, never in session
Decision:     The Wang & Horowitz recomputation was moved out of an interactive
              session into `workflows/32_recompute_wang2026.py`, which rewrites
              all nine tables from `data/raw/` on every run.
Alternatives: Keep the interactive results, since they were already computed
              and agreed with the paper.
Reason:       WORKSPACE.md rule 8. A review that asserts a paper is not
              reproducible has no standing if its own numbers are not. The
              session that produced the first set of tables cannot be rerun by
              a stranger with this repository.
Affects:      workflows/32_recompute_wang2026.py, results/statistical_reviews/
