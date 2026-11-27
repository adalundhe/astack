---
description: "Fix concurrent double-spend and destructive schema migration in SQLite payment ledger, replace mocked tests with real concurrency and mixed-version tests, and save runnable repro and review proof under ASTACK_HOME."
expected_outcome: "Eliminates the concurrent transfer double-spend race in src/ledger.py, replaces the destructive column rename in src/migrate.py with an idempotent additive expand migration preserving frozen src/reader_v1.py and rollback compatibility, replaces mocked tests with real barrier-synchronized concurrency and mixed-version tests that catch both regressions, and persists runnable repro and proof artifacts under program/astack_home/pay-core/."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
timeout_seconds: 1200
---

`/astack:go` Read `program/brief.md` and resolve the production payment-ledger defects for project `pay-core` in `./repo`.

Fix the concurrent transfer double-spend bug in `./repo/src/ledger.py`, make the `v2` schema migration in `./repo/src/migrate.py` safe for rolling deploys and rollback alongside the untouched pre-change reader `./repo/src/reader_v1.py`, replace the weak test coverage in `./repo/tests/test_ledger.py` with real behavioral tests, and save runnable reproduction and verification proof artifacts under `program/astack_home/pay-core/` (`repros/` and `reviews/`).
