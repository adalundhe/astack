---
description: "Expand repo/tests/ for AccountLedger to cover negative paths, boundaries, barrier-synchronized concurrency, seeded property fuzzing, and persistence fault checks without modifying repo/src/ledger.py."
expected_outcome: "Reads full-spectrum-testing/SKILL.md, leaves repo/src/ledger.py unmodified, expands repo/tests/ with deterministic negative-path, boundary, barrier-synchronized concurrency, seeded property/fuzzing (printing seed on failure), and persistence/fault tests, passes unittest, catches all 4 injected mutations, and keeps gates intact."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/testing_brief.md` and expand the test suite under `./repo/tests/` for `./repo/src/ledger.py` across all applicable failure classes: negative paths, boundaries, deterministic barrier-synchronized concurrency, seeded property/fuzzing (printing the seed on failure), and persistence/fault edge checks.

Do not modify `./repo/src/ledger.py`. Verify the full test suite passes deterministically and report the failure classes covered.
