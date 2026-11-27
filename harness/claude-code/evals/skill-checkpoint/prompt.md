---
description: "Persist a durable handoff checkpoint for branch lane/billing capturing branch, commit SHA, completed step 1, remaining step 2, and exact verification command."
expected_outcome: "Reads checkpoint/SKILL.md, keeps ./repo clean on branch lane/billing, and writes program/CHECKPOINT.md with the branch name, current commit SHA, completed step 1 summary, remaining step 2 description, and exact unittest verification command."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` We need to save a durable checkpoint for the active billing work in `./repo` (on branch `lane/billing`) before stopping for now. The program is running in `agentic-only` mode (see `program/settings.json`), step 1 is already committed, and the plan/log live in `program/LANES.md`.

Inspect `./repo` and `program/LANES.md`, verify the current tests pass, and write a durable handoff checkpoint to `program/CHECKPOINT.md` capturing:
- the git branch name (`lane/billing`)
- the current commit SHA
- completed work (step 1)
- remaining work (step 2)
- the exact verification command

Do not start implementing step 2 and leave `./repo` clean.
