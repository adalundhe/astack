---
type: llm
---

Evaluate the changes in `./repo` and the final summary against `minimize-state-stores`.

PASS if all of these hold:
- Removes `_GLOBAL_BALANCE_CACHE`, `_balance_cache`, and `_summary_cache` (no redundant unmeasured shadow stores or mutable globals remain).
- `get_balance`, `account_summary`, and `all_balances` derive their values directly from the primary ledger entries.
- Separate `BillingLedger` instances do not share mutable state.
- Unit tests cover charges, refunds, adjustments, voids, and cross-instance isolation and pass.

FAIL otherwise.
