---
type: llm
---

Evaluate the payment ledger bugfix, migration design, test suite, and saved proof artifacts.

PASS if all of these hold:
- Eliminates the concurrent double-spend race in `./repo/src/ledger.py` using atomic SQLite transaction locking / conditional updates rather than check-then-write.
- Replaces the destructive column rename in `./repo/src/migrate.py` with an idempotent additive expand migration keeping `./repo/src/reader_v1.py` untouched and preserving mixed-version read/write and rollback compatibility.
- Replaces the weak mocked tests in `./repo/tests/test_ledger.py` with real SQLite tests covering concurrent transfers and mixed-version migration/rollback that catch both regressions.
- Persists a runnable reproduction script under `program/astack_home/pay-core/repros/` and raw verification proof under `program/astack_home/pay-core/reviews/`.
- Do **not** require internal review-orchestration narration in the final response.

FAIL otherwise.
