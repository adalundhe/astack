---
type: llm
---

Evaluate the bug fix, regression test, write scope, and final summary against `fix-it`.

PASS if all of these hold:
- Adds a regression test in `./repo/tests/test_tax.py` reproducing the `.5`-cent half-up rounding bug before fixing it.
- Fixes `./repo/src/tax.py` minimally for exact half-up rounding without touching `./repo/src/auth.py` or `./repo/src/billing.py`.
- Leaves zero debug files behind, passes all unit tests and mutation checks, keeps all gates intact, and reports the before/after verification.

FAIL otherwise.
