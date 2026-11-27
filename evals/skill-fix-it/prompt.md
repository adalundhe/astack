---
description: "Apply a minimal, test-first fix for the half-up rounding bug in repo/src/tax.py without making out-of-scope edits to repo/src/auth.py or repo/src/billing.py."
expected_outcome: "Reads fix-it/SKILL.md, writes a red-first regression test in repo/tests/test_tax.py, fixes only repo/src/tax.py for half-up rounding while leaving repo/src/auth.py and repo/src/billing.py completely untouched, passes unittest and mutation check, and keeps gates intact."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/bug_ticket.md` and fix the confirmed rounding bug in `./repo/src/tax.py`.

Write a failing regression test first, apply the minimal root-cause fix strictly inside the fault boundary without refactoring unrelated modules, verify the full test suite passes, and report the before/after proof.
