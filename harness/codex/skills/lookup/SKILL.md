---
name: lookup
description: "Consult saved per-project LESSON.md memories in ~/.astack/<project_name>/lessons/<lesson_name>/, past decisions, environment catalogs, and cross-project history to determine the best path, avoid dead ends, discover relevant repos on cross-repo work, or familiarize yourself with a task, project, or environment. Use whenever checking memories, researching how a project does things, starting unfamiliar or cross-repo work, or determining which repos a request touches."
---

# Lookup

Check what previous work already proved before guessing, re-exploring from scratch, or repeating known dead ends.

1. **Consult memories early and often:** run **lookup** whenever you are familiarizing yourself with a project or environment, starting an unfamiliar task or plan (**dagify**, **treeify**, **cross-repo**), choosing between implementation or deployment paths, debugging a recurring area, checking how a repo/team does something (**rtfm**), or auditing why a rule slipped (**bap**).
2. **Search `~/.astack` first, then adjacent durable memory (Windows, macOS, and Linux):**
   - **Canonical per-project lessons store:** `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` (`$HOME/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` on macOS/Linux; `%USERPROFILE%\.astack\<project_name>\lessons\<lesson_name>\LESSON.md` on Windows; override via `ASTACK_HOME` only when configured). Use `astack-tools lessons list` (filterable via `--project <slug>`, `--related <slug>`, `--keyword <term>`, `--status active`, `--json`) to scan YAML frontmatter (`lesson`, `project`, `related_projects`, `keywords`, `status`, `created`, `updated` in `YYYY-MM-DDTHH:MMZ`) cheaply across projects, or scan `Path.home() / ".astack"` with UTF-8 reads (`encoding="utf-8"`). Never assume lessons live inside a git repo (`<repo>/lessons/...`).
   - **Cross-repo & cross-project lookup (and repo discovery):** whenever a task is cross-repo or cross-project—or might touch upstream/downstream services, shared packages, IaC/infra, auth, or deploy pipelines—**do not stop at the current repo's folder**. Search lessons across **all** relevant `<project_name>` directories under `~/.astack/` (`astack-tools lessons list --related <project>` and `--keyword <domain>`) AND **use saved lessons across `~/.astack/*/lessons/*/LESSON.md` (`related_projects`, `keywords`, `## References`, deploy sequences, API/schema seams, and past blast-radius notes) to determine which other repos or projects might be relevant to the work**, then confirm those candidate repos exist and apply via **rtfm** / **cross-repo**.
   - **Adjacent durable memory:** program `LANES.md` `decided:` / `person:` logs (`astack-decisions`), `RULES.md`, `TOOLS.md` (**analyze-environment**), flat `LESSONS.md` if present, ADRs, runbooks, and repo guides (**rtfm**).
   - Search by project name, `related_projects`, `keywords`, subsystem, error signature, tool/platform, and task goal—read matching `LESSON.md` files in full (`## Overview`, `## Skills and tools used`, `## Details`, `## Successes`, `## Issues`, `## Best path & guards`, `## References`) rather than guessing from folder names.
3. **Verify retrieved memories against current reality (past lessons are hypotheses, not gospel):**
   - Check frontmatter `status` (`active` vs `tentative` vs `superseded`), `updated` timestamp, and `## Overview`'s **Applies when / Does not apply when** boundaries: does the lesson still fit today's codebase, OS/environment, scale, and constraints?
   - Confirm cited repos, file paths, flags, commands, defaults, and assumptions against the live repo(s) and environment (**rtfm**, **prove-it**). Current code and live behavior always outrank a stale note.
4. **Synthesize before acting:** distill what applies into tight points for your plan or report—
   - **Relevant repos & projects:** any additional repos/projects uncovered from `~/.astack` lessons (`related_projects` / `## References`) that this work touches or depends on.
   - **Best path, skills & tools:** proven patterns, commands, skills, and tools from `## Successes`, `## Skills and tools used`, and `## Best path & guards` that still hold.
   - **Pitfalls & dead ends to avoid:** failures, rejected theories, rollout hazards, and environment quirks from `## Issues`.
   - **Stale notes or missing memory:** flag any contradicted `LESSON.md` for updating/superseding, and if critical history only exists in raw uncaptured chats, tickets, bugs, or deploy logs, run **lookback** to dig in and record a durable `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`.

Referenced skills: `dagify` (`../dagify/SKILL.md`), `treeify` (`../treeify/SKILL.md`), `cross-repo` (`../cross-repo/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `bap` (`../bap/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `lookback` (`../lookback/SKILL.md`). Read any cited skill file before acting when its trigger applies.
