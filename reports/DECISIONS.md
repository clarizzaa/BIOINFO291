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
