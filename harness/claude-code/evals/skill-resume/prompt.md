---
description: "Resume a paused branch from SUSPENDED.md and LANES.md, keep step 1 intact, complete step 2 (retry cap in src/sync.py + tests), pass mutation checks, and log resumption."
expected_outcome: "Reads resume/SKILL.md, resumes lane/sync from program/SUSPENDED.md while keeping step 1 (checkpoint_offset) intact, enforces max_retries cap in repo/src/sync.py with regression tests, passes unittest, mutation check, and gate checks, and appends a UTC-stamped resumption entry to program/LANES.md."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Resume the paused sync lane in `./repo` (branch `lane/sync`) using the handoff in `program/SUSPENDED.md` and `program/LANES.md` (`agentic-only` mode per `program/settings.json`).

1. Inspect `program/SUSPENDED.md` and `program/LANES.md` and verify step 1 (`checkpoint_offset`) remains intact without duplicating completed work.
2. Complete step 2: enforce the `max_retries` retry cap in `./repo/src/sync.py` (total attempts = `1 + max_retries`, raising `ValueError` for negative `max_retries` and re-raising `TransientSyncError` once exhausted) and add regression tests in `./repo/tests/test_sync.py`.
3. Verify the full test suite passes and append a UTC-stamped resumption entry under `## Log` in `program/LANES.md`.
