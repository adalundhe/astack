---
description: "A small, isolated low-risk change under Go mode spawns one astack:reviewer agent (preferring a non-worker model), stops on a clean single review, saves the internal coverage map to disk, and returns a concise user-facing summary without leaking internal ledger status."
expected_outcome: "Reads review/SKILL.md, classifies the change as low-risk, spawns one astack:reviewer agent on sonnet, stops cleanly via astack-review-ledger (saving internal coverage map to program/coverage-map.md), and returns a clean user-facing summary with zero leaked internal ledger status."
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Run a vectored review of the branch `lane/collapse-spaces` vs `main` in `repo/` (diff also saved at `program/change.diff`, base files at `program/base/`) using ONLY the approved `reviewer_pool` in `program/settings.json`. The worker built this change on `anthropic/haiku`. Review it as a single vector, run `astack-review-ledger` saving the internal coverage map to `program/coverage-map.md`, and give me a concise user-facing summary without leaking internal ledger status codes.
