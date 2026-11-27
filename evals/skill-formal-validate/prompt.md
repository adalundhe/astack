---
description: "Write a deterministic exhaustive state-space checker for repo/src/lease.py, capture the mutual-exclusion counterexample in program/counterexample.json, fix the lease bug, and prove 0 violations across all reachable states."
expected_outcome: "Reads formal-validate/SKILL.md, writes deterministic exhaustive state-space model checker program/check_model.py against repo/src/lease.py, captures the buggy mutual-exclusion counterexample trace in program/counterexample.json, fixes repo/src/lease.py and replays the trace as a unit test, confirms 0 reachable invariant violations on fixed code while catching the buggy code, and passes unittest, mutation check, and gate check."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/validate_brief.md` and formally validate the mutual-exclusion safety invariant of the distributed lease state machine in `./repo/src/lease.py`.

Build a deterministic exhaustive state-space checker at `program/check_model.py`, record the counterexample trace found on the current buggy code in `program/counterexample.json`, fix the root cause in `./repo/src/lease.py` with a counterexample replay unit test in `./repo/tests/test_lease.py`, and prove the exhaustive checker finds zero violations across all reachable states after the fix.
