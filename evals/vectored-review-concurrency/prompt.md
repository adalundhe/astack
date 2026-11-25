---
description: "Unprompted review of a concurrency-touching change: tests whether the skill itself (without prompt hints) classifies risk, spawns at least two blind reviewers on different models, uses astack-review-ledger, proves the race, blocks landing with a plain-language risk range, and never leaks internal ledger status."
expected_outcome: "Follows review/SKILL.md without prompt spoon-feeding: spawns blind astack:reviewer agents on sonnet and haiku, runs astack-review-ledger, proves the lock-split race, holds landing with a plain-language remaining-bug range, leaves repo/ untouched, and leaks zero internal status."
max_turns: 14
timeout_seconds: 360
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Review branch `lane/concurrent-batch` against `main` in `repo/` before we merge it (diff saved at `program/change.diff`, base at `program/base/pool.py`). Settings are in `program/settings.json`; this branch was built by the worker configured there.
