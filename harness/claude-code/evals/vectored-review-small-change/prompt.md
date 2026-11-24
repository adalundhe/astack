---
description: "A small, isolated low-risk change under Go mode spawns one astack:reviewer agent (preferring a non-worker model) and stops on a clean single review."
expected_outcome: "Reads review/SKILL.md, classifies the change as low-risk, spawns one astack:reviewer agent on a model other than the worker's (sonnet), stops on a clean single review, and opens the report with the coverage map."
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Run a vectored review of the branch `lane/collapse-spaces` vs `main` in `repo/` (diff also saved at `program/change.diff`, base files at `program/base/`) using the approved `reviewer_pool` in `program/settings.json` (do not use any model outside that pool). The worker built this change on `anthropic/haiku`. Review it as a single vector, run `astack-review-ledger`, and open your report with the coverage map.
