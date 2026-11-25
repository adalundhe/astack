---
description: "Zero-hint outcome eval for lookback and lookup: mines a completed session log into a structured LESSON.md under ASTACK_HOME (never inside the repo) and audits/removes or supersedes an obsolete lesson."
expected_outcome: "Reads lookback/SKILL.md, writes a valid 7-section flat-YAML LESSON.md under program/astack_home/billing/lessons/<slug>/LESSON.md (zero repo/lessons or LESSONS.md files), and updates/supersedes/deletes the stale legacy-xml-parser lesson."
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` We just finished debugging an outage in `repo/` (project `billing`); the session log is in `program/session-log.md`. With `ASTACK_HOME` set to `program/astack_home`, review what happened, capture durable lessons for future runs, and audit our existing lessons for `billing` against `repo/`.
