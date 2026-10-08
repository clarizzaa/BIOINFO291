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

Skills and agent profiles created for this project are **mirrored into the
repository** — `skills/<name>/` and `agents/<name>/` — and applied from those
files. The repository copy is the source; the platform copy is a deployment of
it. This keeps web-based configuration under version control, which is the gap
section 4 describes.

| Skill | Purpose | Added |
|---|---|---|
| `figure-contract` | Make a figure that keeps the contract in `docs/figure-contract.md`: the twelve enforced rules, the helper functions that carry them, and the mandatory sidecar. Source: `skills/figure-contract/`. | 2026-10-08 |
| `reproducible-workflow-step` | Add or revise a numbered analysis step under the `WORKSPACE.md` contract: the step template with its Inputs/Outputs/Env header, parameters into `configs/` first, filter counts recorded, the experimental-unit and confounding checks, a `DECISIONS.md` entry in the same commit, and a clean-rerun verification. Ships `scaffold_step`, `decision_entry` and `audit_steps`. Source: `skills/reproducible-workflow-step/`. | 2026-10-08 |

## 3b. Agent profiles

| Profile | Purpose | Access | Added |
|---|---|---|---|
| `FIGURE_REVIEWER` | Reviews a finished figure against `docs/figure-contract.md` and returns a structured verdict. Reports only; does not edit. Source: `agents/figure-reviewer/`. | Restricted: no skills, no connectors | 2026-10-08 |

Applying a profile from its repository source:

    # repl tool
    host.agents.create(
        "FIGURE_REVIEWER", "Figure Reviewer", "<description>",
        system_prompt=open("agents/figure-reviewer/AGENT.md").read(),  # prompt section
        skill_names=[],          # restricted: no skills, and therefore no connectors
    )

The structured output the reviewer must return is
`agents/figure-reviewer/output_schema.json`; pass it as the `output_schema`
when delegating a review.

## 4. Known gaps versus a file-based harness

- No `CLAUDE.md` / `AGENTS.md` support: handled by the project-context text
  above, which points at `WORKSPACE.md`.
- No rules folder: `WORKSPACE.md` plus skills cover the same ground.
- Configuration is web-based, so it is not versioned by git. This file is the
  versioned record of what that configuration says. Skills and agent profiles
  are additionally mirrored as files under `skills/` and `agents/`, so their
  content — not merely their existence — is in the repository.
- **A profile cannot be denied a core tool.** The profile API exposes a
  per-tool blocklist only for *connector* tools; core tools such as
  `edit_file`, `python` and `bash` cannot be withheld from a profile created
  through it. `FIGURE_REVIEWER` is therefore prevented from editing files by
  its system prompt rather than by the harness. The separation of generation
  from review is a convention the agent is instructed to keep, not a
  capability it lacks, and any claim that the reviewer *cannot* edit should be
  read in that light.
- The platform kernel that creates skills and profiles cannot read the granted
  host folder directly, so repository files are staged through the session
  workspace before being applied. Mechanical, but it means "applied from the
  repo" involves a copy step.
