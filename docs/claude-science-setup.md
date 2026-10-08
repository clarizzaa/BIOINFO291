# Running this repo inside Claude Science

Claude Science does not read `CLAUDE.md` or `AGENTS.md`, and it has no rules
folder — its configuration is web-based rather than file-based. The repository
rules therefore have to be injected through the two hooks the harness does
provide. This file records how that is done, so the setup is itself
reproducible.

## 1. Project instructions

Paste the following into **Project settings -> project context** in Claude
Science. It is deliberately short: it delegates to the file in the repo so the
rules never exist in two places and drift apart.

---
This project works inside the git repository at
`~/Documents/BIOINFO291` (github.com/clarizzaa/BIOINFO291).

Before doing anything in this project, read `WORKSPACE.md` at the repository
root and follow it for the whole session. It defines the directory layout,
the data-handling rules, where parameters live, the statistical standards,
and the decision log. `reports/DECISIONS.md` records choices already made —
read it before proposing an analysis, and append to it when you make a new
consequential choice.

Work on files in the repository, not in the ephemeral session workspace.
Commit after each meaningful step.
---

## 2. Host folder access

The repository lives on the local machine, so the sandbox needs a read-write
grant for `~/Documents/BIOINFO291`. The grant is narrow on purpose: a grant on
`~/Documents` would hand the agent authority over every unrelated file there.

## 3. Skills

Steps that get repeated become skills, so the procedure is encoded once rather
than re-explained each session. Skills created for this project are recorded
here as they are added.

| Skill | Purpose | Added |
|---|---|---|
| _(none yet)_ | | |

## 4. Known gaps versus a file-based harness

- No `CLAUDE.md` / `AGENTS.md` support: handled by the project-context text
  above, which points at `WORKSPACE.md`.
- No rules folder: `WORKSPACE.md` plus skills cover the same ground.
- Configuration is web-based, so it is not versioned by git. This file is the
  versioned record of what that configuration says.
