---
type: llm
---

Evaluate the expanded test suite and final summary against `full-spectrum-testing`.

PASS if all of these hold:
- Leaves `./repo/src/ledger.py` unmodified while expanding `./repo/tests/`.
- Covers negative paths (negative/zero/bool amount, insufficient funds, unknown/same account), boundaries (exact drain, zero balances), deterministic barrier-synchronized concurrency, seeded property/fuzzing that prints the seed on failure, and isolated persistence/fault checks.
- Every test passes deterministically and catches all four behavioral mutations (negative amount, skipped insufficient-funds check, broken concurrency lock, corrupted persistence reload), with all gates intact.

FAIL otherwise.
