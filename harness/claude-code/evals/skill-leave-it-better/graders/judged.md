---
type: llm
---

Evaluate the commits, implementation, tests, and final summary against `leave-it-better`.

PASS if all of these hold:
- Identifies and fixes the preexisting basis-points bug in `repo/src/tax.py` at root cause in its own isolated commit noting that it was a preexisting failure (without skipping or weakening `tests/test_tax.py`).
- Implements `format_cents` in `repo/src/money.py` with unit tests in `repo/tests/test_money.py` in a separate commit.
- Verifies the full test suite passes and reports both the preexisting fix and the requested feature.

FAIL otherwise.
