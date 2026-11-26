---
name: lookup
description: "Consult ~/.astack lessons, architecture decisions, and review evidence bundles before acting. Use when starting unfamiliar work, planning, debugging recurring areas, or discovering related repos."
disable-model-invocation: true
---

# Lookup

Check what past work proved before guessing, re-exploring, or repeating dead ends.

## 1. Consult memories early and often

Run `lookup` before unfamiliar work, planning (`dagify`, `treeify`, `cross-repo`), or choosing a path. Also run it for recurring bugs, repo conventions (**rtfm**), or rule audits (`bap`).

## 2. Search `~/.astack` first, then adjacent durable memory

- **Canonical lessons store:** `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` (`%USERPROFILE%\.astack\...` on Windows; `ASTACK_HOME` overrides). Filter frontmatter cheaply via `astack-tools lessons list` (`--project`, `--related`, `--keyword`, `--status active`, `--json`). Never assume lessons live in `<repo>/lessons/...`.
- **Architecture decisions store:** `~/.astack/<project_name>/architecture/AD_<N>.md` (`astack-tools arch list --project <project_name>`). Read relevant ADs in full alongside any repo-local ADRs.
- **Review evidence store:** `~/.astack/<project_name>/reviews/<date_time>/` (`astack-tools reviews list --project <project_name>`). Examine past review verdicts and saved `prove-it` artifacts to catch recurring failure modes and prior baselines.
- **Repros store:** `~/.astack/<project_name>/repros/<repro>/` (`astack-tools repros list --project <project_name>`). Reuse saved standalone reproduction scripts and shrunk test cases before rebuilding them from scratch.
- **Automations store:** `~/.astack/<project_name>/automations/<automation_name>/` (`astack-tools automations list --project <project_name>`). Check saved Werkflow, Orchestral, and TaskEx automations before recreating recurring workflows.
- **Research store:** `~/.astack/<project_name>/research/` (`astack-tools research list --project <project_name>`). Reuse verified external research, specs, and primary-source briefs before re-fetching.
- **Docs store:** `~/.astack/<project_name>/docs/` (`astack-tools docs list --project <project_name>`, including `docs/contracts/`). Read saved project docs, contract catalogs, and connection guides.
- **Logging store:** `~/.astack/<project_name>/logging/<logs|traces|metrics>/` (`astack-tools logging list --project <project_name>`). Inspect prior timestamped logs, traces, and metrics before re-capturing.
- **Cross-repo or cross-project lookup & repo discovery:** look beyond the current repo when work touches shared services, packages, IaC, auth, or deploys. Scan `~/.astack/*/lessons/*/LESSON.md` (`related_projects`, `keywords`, `## References`) to **determine which other repos or projects might be relevant**. Verify candidate repos via **rtfm** or `cross-repo`.
- **Adjacent durable memory:** read `LANES.md` (`astack-decisions`), `RULES.md`, `TOOLS.md` (`analyze-environment`), repo ADRs, runbooks, and repo guides (**rtfm**).
- Read matching `LESSON.md` files and cited review artifacts in full rather than guessing from folder names. Never skim, because boundaries, raw evidence, and rejected theories live inside the files.

## 3. Verify memories against live reality

Past lessons are hypotheses, not gospel, because code and environments drift. Check `status`, `updated`, and `## Overview` boundaries. Confirm cited paths, commands, and defaults against live code (**rtfm**, `prove-it`). Live behavior always outranks a stale note.

## 4. Synthesize before acting

Distill what applies into four short points:

- **Relevant repos & projects:** extra repos surfaced from `related_projects` or `## References`.
- **Best path, skills & tools:** proven patterns from `## Successes` and `## Best path & guards`.
- **Pitfalls to avoid:** failures, rejected theories, and traps from `## Issues`.
- **Stale or missing memory:** flag contradicted lessons for update. Run **lookback** when key history sits uncaptured in chats, tickets, or logs.

**Done when:** matching lessons and adjacent memories are verified against live code and distilled into those four points.

Referenced skills: `rtfm` (`../rtfm/SKILL.md`), `lookback` (`../lookback/SKILL.md`). Read any cited skill file before acting when its trigger applies.
