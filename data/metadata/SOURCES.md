# Data sources

One entry per file in `data/raw/`. No raw file may exist without an entry.

Checksums are produced with:

    shasum -a 256 data/raw/<file>

| File | Source (URL / accession) | Obtained | SHA-256 | Notes |
|---|---|---|---|---|
| `GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz` | [GSE120575](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE120nnn/GSE120575/suppl/GSE120575_Sade_Feldman_melanoma_single_cells_TPM_GEO.txt.gz) | 2026-10-08 | `43fa3d50acd151be89aa8e94ac83cc730dbbf7623473339c5534b77c16d48e3f` | log2(TPM+1) matrix, genes x cells, as released by the authors |
| `GSE120575_patient_ID_single_cells.txt.gz` | [GSE120575](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE120nnn/GSE120575/suppl/GSE120575_patient_ID_single_cells.txt.gz) | 2026-10-08 | `6a228029df713006fb465f02cc3e1e17540b0ddaf4b69374b116aeb135cdf73f` | per-cell sample, patient, timepoint, therapy and response labels |
| `chickweight.csv` | `datasets::ChickWeight`, R 4.5.3 (2026-03-11); exported by `workflows/20_get_chickweight.R`. Originally Crowder & Hand (1990); Pinheiro & Bates (2000) | 2026-10-08 | `7e04dfcf38df4ae2696d27a9e2edc569406da622db777297abcbda88249a45fd` | 578 weighings of 50 chicks on 4 diets; columns chick, diet, time (days), weight (g). Week-2 data-visualization dataset. Not downloaded: it ships with base R, so the R version is the thing that pins it. Full provenance in `chickweight_provenance.txt` |
| `papers/wang2026-conspecific-odors/paper.pdf` | [doi:10.1038/s41598-026-41426-1](https://doi.org/10.1038/s41598-026-41426-1) | 2026-10-15 | `3a1788c93d4fc983d7521a2c60abbdb744214939d99f4fba88baf487ab3ab4de` | article PDF as published (open access) |
| `papers/wang2026-conspecific-odors/Part_1.xlsx` | [doi:10.5061/dryad.bzkh189pt](https://doi.org/10.5061/dryad.bzkh189pt) (Dryad) | 2026-10-15 | `3ef960171f504113ed0aab0e5841250e07dfaf42cc46c350f7fa2ee709f20d90` | deposited by the authors of wang2026-conspecific-odors |
| `papers/wang2026-conspecific-odors/Part_2.xlsx` | [doi:10.5061/dryad.bzkh189pt](https://doi.org/10.5061/dryad.bzkh189pt) (Dryad) | 2026-10-15 | `fb594cabc647751d5b4a9944a20700230785ec24a3a1dfa466718edcc98eee1e` | deposited by the authors of wang2026-conspecific-odors |
| `papers/wang2026-conspecific-odors/README.md` | [doi:10.5061/dryad.bzkh189pt](https://doi.org/10.5061/dryad.bzkh189pt) (Dryad) | 2026-10-15 | `c39250e094ef2b68b2aa0aef7df9d093f53644db7d3e8bdfbc3de00b7b7ffb06` | deposited by the authors of wang2026-conspecific-odors |
| `papers/wang2026-conspecific-odors/statistical_analyses.R` | [doi:10.5061/dryad.bzkh189pt](https://doi.org/10.5061/dryad.bzkh189pt) (Dryad) | 2026-10-15 | `bf63d0a9271a09a8b256c69a24e65571d9c304875b26504a406f2bc64317366f` | deposited by the authors of wang2026-conspecific-odors |
| `papers/goold2016-behavioural-networks/paper.pdf` | [doi:10.1098/rsos.160268](https://doi.org/10.1098/rsos.160268) | 2026-10-15 | `70d990207f44e233060a5269a98fede6ee83cf6448278965f0d432762c5e089a` | article PDF as published (open access) |
| `papers/goold2016-behavioural-networks/DetectionDog_GGM_AssociationMatrix.csv` | [doi:10.5061/dryad.81k11](https://doi.org/10.5061/dryad.81k11) (Dryad) | 2026-10-15 | `5fc8a6354a65a3db3bd17bac851a9e4c2dcf8cd5d763d10326c00c909b5c3e7c` | deposited by the authors of goold2016-behavioural-networks |
| `papers/goold2016-behavioural-networks/finalMIdata_averaged_rounded.csv` | [doi:10.5061/dryad.81k11](https://doi.org/10.5061/dryad.81k11) (Dryad) | 2026-10-15 | `d4d76f3822830936d923ccaa4dd8374c03a74a605e22c26c416a62da019d4678` | deposited by the authors of goold2016-behavioural-networks |
| `papers/goold2016-behavioural-networks/PatrolDog_GGM_AssociationMatrix.csv` | [doi:10.5061/dryad.81k11](https://doi.org/10.5061/dryad.81k11) (Dryad) | 2026-10-15 | `73d603fa6a7313e484102fb7d32c815a03490fe18b03ed72bb89fc988c639a26` | deposited by the authors of goold2016-behavioural-networks |
| `papers/goold2016-behavioural-networks/rawData.csv` | [doi:10.5061/dryad.81k11](https://doi.org/10.5061/dryad.81k11) (Dryad) | 2026-10-15 | `4713c991b05722f0034079d7f807f113d546440e5f152b72d3f852632693ab3b` | deposited by the authors of goold2016-behavioural-networks |
| `papers/goold2016-behavioural-networks/Rscript.R` | [doi:10.5061/dryad.81k11](https://doi.org/10.5061/dryad.81k11) (Dryad) | 2026-10-15 | `9a0af44356647278067be016cd0fe613fea0e67cb2bf4f44504a732a63b77386` | deposited by the authors of goold2016-behavioural-networks |
| `papers/goold2016-behavioural-networks/Supplementary_Material_Revised.pdf` | [doi:10.5061/dryad.81k11](https://doi.org/10.5061/dryad.81k11) (Dryad) | 2026-10-15 | `7b8a45d7fa54405ea6010ef800e582499869ba73709f0898ce594cf1158c08f0` | deposited by the authors of goold2016-behavioural-networks |

