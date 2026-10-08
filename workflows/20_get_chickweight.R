#!/usr/bin/env Rscript
# 20_get_chickweight.R
#
# Inputs:  R `datasets` package (base R), no network access required
# Outputs: data/raw/chickweight.csv
#          data/metadata/chickweight_provenance.txt  (versions, date, SHA-256)
#
# ChickWeight is a built-in R dataset, so "obtaining" it means pinning which R
# version produced the file. Run once; data/raw/ is read-only thereafter
# (WORKSPACE.md rule 1).

args <- commandArgs(trailingOnly = FALSE)
this <- sub("^--file=", "", args[grep("^--file=", args)])
repo <- if (length(this)) normalizePath(file.path(dirname(this[1]), "..")) else getwd()
if (!dir.exists(file.path(repo, "data", "raw"))) {
  stop("cannot locate the repository root from ", repo)
}

out_csv <- file.path(repo, "data", "raw", "chickweight.csv")
out_prov <- file.path(repo, "data", "metadata", "chickweight_provenance.txt")

if (file.exists(out_csv)) {
  stop("data/raw/chickweight.csv already exists; data/raw is read-only. ",
       "Delete it deliberately if you intend to regenerate.")
}

d <- datasets::ChickWeight
d <- data.frame(
  chick  = as.integer(as.character(d$Chick)),
  diet   = as.integer(as.character(d$Diet)),
  time   = as.integer(d$Time),
  weight = as.numeric(d$weight)
)
d <- d[order(d$chick, d$time), ]

write.csv(d, out_csv, row.names = FALSE, quote = FALSE)

digest <- if (requireNamespace("openssl", quietly = TRUE)) {
  as.character(openssl::sha256(file(out_csv)))
} else {
  trimws(strsplit(system2("shasum", c("-a", "256", out_csv),
                          stdout = TRUE), " +")[[1]][1])
}

writeLines(c(
  "ChickWeight provenance",
  "",
  paste("source:      R datasets package (base R), datasets::ChickWeight"),
  paste("reference:   Crowder & Hand (1990); Pinheiro & Bates (2000)"),
  paste("obtained:    ", format(Sys.Date())),
  paste("R version:   ", R.version.string),
  paste("rows:        ", nrow(d)),
  paste("chicks:      ", length(unique(d$chick))),
  paste("sha256:      ", digest),
  "",
  "Columns: chick (id), diet (1-4), time (days since hatch), weight (grams)."
), out_prov)

cat("wrote", out_csv, "\n")
cat("rows:", nrow(d), " chicks:", length(unique(d$chick)), "\n")
cat("sha256:", digest, "\n")
