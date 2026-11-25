---
description: "Unprompted review of a high-risk auth change with a cross-harness reviewer_pool: tests whether the skill itself checks pool reachability via astack-dispatch, never substitutes unapproved models, proves the auth bugs, holds landing on non-convergence, and never leaks internal status."
expected_outcome: "Follows review/SKILL.md without prompt spoon-feeding: checks pool reachability with astack-dispatch, dispatches reachable approved models across harnesses (never substituting an unapproved model), proves the expired-refresh and timing-comparison bugs, runs astack-review-ledger, holds landing with a plain-language escalation if non-converged, and leaks zero internal status."
max_turns: 14
timeout_seconds: 360
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Review branch `lane/token-refresh` against `main` in `repo/` before we merge it (diff saved at `program/change.diff`, base file at `program/base/auth.py`). Settings are in `program/settings.json`; this branch was built by the worker configured there.
