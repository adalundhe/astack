---
description: "Zero-hint outcome eval for the merged find-it -> fix-it flow: confirms a real multi-record workload failure, shrinks the repro before narrowing the root cause, fixes an implicit-state bug minimally with a red-first behavior test, provides runnable before/after proof, and cleans all debug artifacts."
expected_outcome: "Reads find-it and fix-it, reproduces on the 120-event billing workload, shrinks the repro before diagnosing, fixes the implicit retry-state leak in InvoiceProcessor with explicit per-event/state handling and a behavior test (red on main, green after fix), provides runnable before/after proof, and leaves zero *_DEBUG_*.* artifacts."
max_turns: 16
timeout_seconds: 360
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Customers report wrong invoice totals in `repo/` when processing `program/billing_events.json` (run `python3 repo/src/cli.py program/billing_events.json`; see `repo/README.md` for the billing rules). Investigate the failure on the real workload, find and fix the root cause cleanly with proper tests, prove the fix works before and after, and leave the repo clean.
