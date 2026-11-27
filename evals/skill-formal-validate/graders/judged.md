---
type: llm
---

Evaluate the formal model checker, counterexample trace, lease fix, tests, and final summary against `formal-validate`.

PASS if all of these hold:
- Builds a faithful deterministic exhaustive state-space checker (`program/check_model.py`) exercising `./repo/src/lease.py` on the mutual-exclusion invariant without weakening the property.
- Captures the shortest counterexample trace showing two simultaneous active holders on the buggy lease implementation in `program/counterexample.json`.
- Fixes `./repo/src/lease.py` at root cause and replays the counterexample as a unit test in `./repo/tests/test_lease.py`.
- Proves the checker catches the buggy version (non-zero exit) and passes with zero reachable invariant violations on the fixed version, while unit tests and gate checks pass.

FAIL otherwise.
