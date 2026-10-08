# Data sources

One entry per file in `data/raw/`. No raw file may exist without an entry.

Checksums are produced with:

    shasum -a 256 data/raw/<file>

| File | Source (URL / accession) | Obtained | SHA-256 | Notes |
|---|---|---|---|---|
| `GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz` | [GSE120575](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE120nnn/GSE120575/suppl/GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz) | 2026-10-08 | `43fa3d50acd151be89aa8e94ac83cc730dbbf7623473339c5534b77c16d48e3f` | log2(TPM+1) matrix, genes x cells, as released by the authors |
| `GSE120575_patient_ID_single_cells.txt.gz` | [GSE120575](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE120nnn/GSE120575/suppl/GSE120575_patient_ID_single_cells.txt.gz) | 2026-10-08 | `6a228029df713006fb465f02cc3e1e17540b0ddaf4b69374b116aeb135cdf73f` | per-cell sample, patient, timepoint, therapy and response labels |
| `chickweight.csv` | `datasets::ChickWeight`, R 4.5.3 (2026-03-11); exported by `workflows/20_get_chickweight.R`. Originally Crowder & Hand (1990); Pinheiro & Bates (2000) | 2026-10-08 | `7e04dfcf38df4ae2696d27a9e2edc569406da622db777297abcbda88249a45fd` | 578 weighings of 50 chicks on 4 diets; columns chick, diet, time (days), weight (g). Week-2 data-visualization dataset. Not downloaded: it ships with base R, so the R version is the thing that pins it. Full provenance in `chickweight_provenance.txt` |

