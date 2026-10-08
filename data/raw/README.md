# data/raw — original inputs, READ-ONLY

Files here are exactly as obtained from the source. They are **never** edited,
renamed, or overwritten by any script in this repo.

- The data bytes are **not tracked in git** (see `.gitignore`). Provenance is.
- Every file must have an entry in `../metadata/SOURCES.md` giving the source
  URL/accession, download date, and SHA-256 checksum.
- After downloading, make the files read-only:  `chmod -w data/raw/<file>`

If a raw file needs fixing, the fix is a script in `workflows/` that writes to
`data/processed/`. The original stays untouched.
