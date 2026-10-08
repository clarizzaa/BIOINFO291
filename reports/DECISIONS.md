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

## 2026-10-07  One rules file, several entry points
Decision:     WORKSPACE.md holds the rules; AGENTS.md and CLAUDE.md point to
              it; the Claude Science project-context text also points to it and
              is recorded in docs/claude-science-setup.md.
Alternatives: Duplicate the rules into each harness-specific file.
Reason:       Claude Science supports neither CLAUDE.md nor a rules folder, so
              the rules must be injected through project settings. Duplicating
              them guarantees drift; a pointer does not.
Affects:      WORKSPACE.md, AGENTS.md, CLAUDE.md, docs/claude-science-setup.md
