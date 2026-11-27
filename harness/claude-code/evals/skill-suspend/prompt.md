---
description: "Suspend an active branch with green uncommitted WIP edits by committing WIP safely, appending a UTC-stamped pause entry in LANES.md, and writing a SUSPENDED.md handoff."
expected_outcome: "Reads suspend/SKILL.md, preserves and commits the green WIP edits onto lane/sync so git status is clean, appends a UTC-stamped pause entry under ## Log in program/LANES.md, and writes program/SUSPENDED.md with branch, saved SHA, and exact resume command."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` We need to pause/suspend active work on branch `lane/sync` in `./repo` without losing progress. There are green uncommitted WIP edits in `./repo`, and the lane log is at `program/LANES.md` (running in `agentic-only` mode per `program/settings.json`).

Suspend this lane safely:
1. Verify tests pass with the current WIP edits and commit the WIP safely onto `lane/sync` so `./repo` is clean and no work is dropped.
2. Append a UTC-stamped pause entry under `## Log` in `program/LANES.md` (preserving the existing header and prior log lines).
3. Write `program/SUSPENDED.md` recording the branch (`lane/sync`), saved commit SHA, paused state, and exact resume command for the next session.
