---
description: "A concurrency-touching change under Go mode triggers a risky vector and spawns at least two blind astack:reviewer agents on different models from reviewer_pool."
expected_outcome: "Reads review/SKILL.md, classifies the concurrency vector as risky, spawns at least two astack:reviewer agents on different approved models (sonnet and haiku) from program/settings.json, and opens the report with the coverage map."
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Run a vectored review of the branch `lane/concurrent-batch` vs `main` in `repo/` (diff also saved at `program/change.diff`, base file at `program/base/pool.py`) using the approved `reviewer_pool` in `program/settings.json` (do not use any model outside that pool). The worker built this change on `anthropic/haiku`. Review only the concurrency vector, run `astack-review-ledger`, and open your report with the coverage map.
