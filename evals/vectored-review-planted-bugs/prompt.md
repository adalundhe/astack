---
description: "Outcome eval with three planted blocking bugs of varying difficulty (easy input validation, medium concurrency race, hard snapshot persistence data loss) plus a minor nit: proves the cautious stopping rule does not stop early at two reviewers while blocking bugs remain, merges overlaps by fix-equivalence, keeps minor findings out of the stopping estimate, and does not leak internal ledger status."
expected_outcome: "Classifies the change as risky, dispatches blind reviewers from the 3-model reviewer_pool (continuing past 2 reviewers via the cautious bound into 3-reviewer M_h jackknife), proves blocking bugs on rerun, decides overlap by fix-equivalence, keeps minor nits out of the stopping math, saves internal coverage map to program/coverage-map.md, and reports the proven blocking bugs cleanly without leaking internal ledger status."
max_turns: 16
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Run a vectored review of the branch `lane/batch-transfer` vs `main` in `repo/` (diff also saved at `program/change.diff`, base file at `program/base/ledger_store.py`) using ONLY the approved `reviewer_pool` in `program/settings.json`. The worker built this change on `anthropic/haiku`. Review it as a single risky vector (`batch-and-persistence`), count only proven blocking bugs in `astack-review-ledger`, verify any shared root cause by fix-equivalence (`equivalence_checks`), quietly save internal audit logs under `program/`, and reply to me with **only** the proven, high-signal issues found (do not mention internal ledger status, coverage-map files, or which/how many reviewer models ran unless a risky risk-acceptance decision is needed).
