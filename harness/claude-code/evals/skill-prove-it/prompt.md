---
description: "Fix the escaped-quote CSV parsing bug in repo/src/csv_stream.py with a deterministic fail-before/pass-after repro under program/astack_home/etl/repros/ and raw before/after proof outputs under program/astack_home/etl/reviews/."
expected_outcome: "Reads prove-it/SKILL.md, saves a standalone repro script under program/astack_home/etl/repros/ that fails on root commit and passes after the fix, stores raw before/after command outputs under program/astack_home/etl/reviews/, fixes repo/src/csv_stream.py with unit tests, passes unittest and mutation check, keeps gates intact, and leaks zero secrets or internal jargon."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/bug_report.md` for project `etl` (with `ASTACK_HOME` set to `./program/astack_home`).

Reproduce the escaped-quote CSV bug deterministically with a standalone repro script saved under `program/astack_home/etl/repros/`, capture raw before-fix and after-fix command outputs under `program/astack_home/etl/reviews/`, fix `./repo/src/csv_stream.py`, add unit tests in `./repo/tests/test_csv_stream.py`, and report your verdict, evidence rung, artifact paths, and exact runnable proof command.
