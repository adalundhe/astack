---
type: llm
---

Evaluate the bug fixes and rewritten test suite against `tests-assert-behaviour`.

PASS if all of these hold:
- Fixes both checkout bugs in `./repo/src/checkout.py`: tax is computed on the post-discount subtotal, and `"FLAT500"` floors at `0`.
- Removes `unittest.mock` / `patch.object` internal helper call-count assertions, tautological expected-value computations, and `time.sleep` from `./repo/tests/test_checkout.py`.
- Tests verify observable totals and typed `ValueError` failures using independent hand-worked expected values across normal, boundary, and error inputs.

FAIL otherwise.
