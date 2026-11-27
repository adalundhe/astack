---
description: "Negative control: a single trivial string typo in ./repo/src/greeting.py is fixed directly without over-routing into planning graphs, bugbash swarms, IaC checks, or formal validation."
expected_outcome: "Fixes the greeting typo in ./repo/src/greeting.py so tests pass, leaves all other files untouched, creates no DAG.md or extra worktrees, and never reads dagify, bugbash, safe-iac, or formal-validate."
timeout_seconds: 180
---

`/astack:go` Fix the greeting typo in `./repo/src/greeting.py` so `format_greeting("Ada")` returns `"Hello, Ada!"` and the unit test in `./repo/tests/test_greeting.py` passes. Keep the change minimal.
