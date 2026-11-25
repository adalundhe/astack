---
name: lookup
description: "Consult saved per-project LESSON.md memories in ~/.astack/<project_name>/lessons/<lesson_name>/, past decisions, environment catalogs, and cross-project history to determine the best path, avoid dead ends, discover relevant repos on cross-repo work, or familiarize yourself with a project or environment."
disable-model-invocation: true
---

# Lookup

Check what previous work already proved before guessing, re-exploring from scratch, or repeating known dead ends.

## 1. Consult memories early and often

Run **lookup** when starting an unfamiliar task or plan (**dagify**, **treeify**, **cross-repo**), choosing between paths, debugging a recurring area, checking repo conventions (**rtfm**), or auditing why a rule slipped (**bap**).

## 2. Search `~/.astack` first, then adjacent durable memory

- **Canonical lessons store:** `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` (`$HOME/.astack/...` on macOS/Linux; `%USERPROFILE%\.astack\...` on Windows; override via `ASTACK_HOME` if configured). Run `astack-tools lessons list` (with `--project`, `--related`, `--keyword`, `--status active`, `--json`) to filter flat YAML frontmatter cheaply across projects. Never assume lessons live inside a git repo (`<repo>/lessons/...`).
- **Cross-repo or cross-project lookup & repo discovery:** do not stop at the current repo's folder when work might span upstream/downstream services, shared packages, IaC, auth, or deploy pipelines. Scan `~/.astack/*/lessons/*/LESSON.md` (`related_projects`, `keywords`, `## References`) to **determine which other repos or projects might be relevant** to the work, then verify those candidate repos exist via **rtfm** or **cross-repo**.
- **Adjacent durable memory:** program `LANES.md` (`astack-decisions`), `RULES.md`, `TOOLS.md` (**analyze-environment**), ADRs, runbooks, and repo guides (**rtfm**).
- Read matching `LESSON.md` files in full rather than guessing from folder names.

## 3. Verify memories against live reality

Past lessons are hypotheses, not gospel, because code and environments drift. Check `status`, `updated`, and `## Overview`'s **Applies when / Does not apply when** boundaries. Confirm cited paths, commands, flags, and defaults against live code (**rtfm**, **prove-it**); live behavior always outranks a stale note.

## 4. Synthesize before acting

Distill what applies into four short points for your plan or report:

- **Relevant repos & projects:** extra repos or projects surfaced from `related_projects` / `## References`.
- **Best path, skills & tools:** proven patterns and commands from `## Successes` and `## Best path & guards`.
- **Pitfalls to avoid:** failures, rejected theories, and rollout traps from `## Issues`.
- **Stale or missing memory:** flag contradicted lessons for updating, and run **lookback** if critical history sits uncaptured in raw chats, tickets, or logs.

Referenced skills: `dagify` (`../dagify/SKILL.md`), `treeify` (`../treeify/SKILL.md`), `cross-repo` (`../cross-repo/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `bap` (`../bap/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `lookback` (`../lookback/SKILL.md`). Read any cited skill file before acting when its trigger applies.
