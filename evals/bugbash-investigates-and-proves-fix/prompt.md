---
description: "Zero-hint outcome eval for the lead-only bugbash workflow: gathers bug report + linked spec/log, swarms blind read-only reviewers with find-it, runs peer challenge to convergence, dispatches a worker with fix-it, instructs post-fix reviewers (given the original bug report + linked docs) to verify with prove-it, and attaches runnable proof/evidence to program/pr-body.md."
expected_outcome: "Reads bugbash/SKILL.md, gathers program/linked-spec.md and program/incident-trace.log, spawns read-only astack:reviewer swarm using find-it (shrinks repro before diagnosing), runs peer challenge to convergence, dispatches astack:worker with fix-it, passes original bug report + linked docs to post-fix reviewers instructed to use prove-it, fixes both tenant-scoping and cached-error bugs in TransferLedger cleanly with red-first tests, attaches runnable before/after proof to program/pr-body.md without internal ledger leaks, and leaves zero debug leftovers."
max_turns: 24
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Run a bugbash on the customer bug reported in `program/bug-report.md` against `repo/` (settings are in `program/settings.json`). Fix the confirmed root cause cleanly on a branch in `repo/`, verify it thoroughly, and write the PR description to `program/pr-body.md`.
