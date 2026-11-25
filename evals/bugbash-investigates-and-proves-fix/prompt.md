---
description: "Zero-hint outcome eval for the lead-only bugbash workflow: gathers bug report + linked spec/log, swarms blind read-only reviewers across reproduction methods with find-it, runs peer challenge to convergence, dispatches a worker with fix-it to implement and resubmit, verifies post-fix with original bug context + prove-it, attaches runnable proof/evidence to program/pr-body.md, and keeps the user-facing reply free of internal process leaks."
expected_outcome: "Reads bugbash/SKILL.md, gathers linked spec and trace, spawns read-only astack:reviewer swarm + astack:worker (verified via tool-call graders), fixes both tenant-scoping and cached-error bugs cleanly with red-first tests, attaches concise runnable proof to program/pr-body.md, and reports proven root causes, fix, and verification plainly without leaking internal process or review-ledger narration."
max_turns: 36
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Run a bugbash on the customer bug reported in `program/bug-report.md` against `repo/` (settings are in `program/settings.json`). Fix the confirmed root cause cleanly on a branch in `repo/`, verify it thoroughly, and write the PR description to `program/pr-body.md`.
