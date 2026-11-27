---
type: llm
---

Evaluate the standalone repro, raw before/after proof artifacts, CSV parser fix, unit tests, and final reply against `prove-it`.

PASS if all of these hold:
- Saves a deterministic standalone repro script under `program/astack_home/etl/repros/` that fails before the fix and passes after the fix.
- Captures raw before-fix and after-fix command outputs under `program/astack_home/etl/reviews/`.
- Fixes `./repo/src/csv_stream.py` to preserve escaped double quotes inside quoted CSV fields and adds unit tests in `./repo/tests/test_csv_stream.py`.
- Reports an explicit verdict (`verified`), trust-ladder rung (rung 5 / running the real system), exact saved artifact paths, and runnable proof command without leaking secrets or internal jargon.

FAIL otherwise.
