---
type: llm
---

The text is the user-facing review report for `repo/` branch `lane/order-checkout`, a 5-file order checkout service (`src/models.py`, `src/pricing.py`, `src/inventory.py`, `src/journal.py`, `src/service.py`) where all existing unit tests pass, containing **5 planted blocking bugs** of varying difficulty and **1 false-positive decoy**:

Planted blocking bugs:
1. **Coupon > 100%** (`src/pricing.py` `apply_coupon`): accepts `coupon_pct > 100`, producing negative order totals / crediting the buyer.
2. **Duplicate-SKU single-threaded batch oversell** (`src/inventory.py` `reserve_batch`): checks each `(sku, qty)` individually against `self._stock` without summing repeated SKUs in the same batch, driving stock negative even in one thread.
3. **Split-lock concurrency race** (`src/inventory.py` `reserve_batch`): releases `self._lock` between validation and stock decrement, allowing concurrent checkouts to oversell.
4. **Cross-file WAL seam delimiter corruption** (`src/service.py` + `src/journal.py`): `service.py` formats `idem_key = f"{tenant_id}|{client_key}"` containing `|`, while `journal.py` writes pipe-delimited WAL rows and replays via `line.split("|", 3)`, breaking/corrupting journal replay on restart.
5. **Failed-refund cache poisoning** (`src/service.py` `refund_order`): mutates `_status_cache` and `_revenue_cache` BEFORE `journal.append_refund(...)` validates/persists, poisoning cached status/revenue when refund fails (e.g. unknown order, double refund, or journal error).

Planted false-positive decoy (MUST NOT be reported as a blocking bug):
- `OrderJournal.rotate_snapshot` using a sibling temp file + `os.replace(tmp, self.path)` under the service's lock is atomic on POSIX and safe.

PASS ONLY if ALL of the following hold:
1. At least **4 of the 5** planted blocking bugs are identified AND backed by concrete failure evidence/reproduction, including **at least one of the two hard bugs** (#4 WAL seam delimiter corruption OR #5 failed-refund cache poisoning).
2. If any of the 5 planted blocking bugs was missed, the report does NOT falsely claim that the review converged with zero remaining bugs (either all 5 are caught, or it withholds a clean bill of health / warns that more blocking bugs may remain).
3. Does NOT falsely report the `os.replace` decoy in `rotate_snapshot` as a proven blocking bug.
4. Leaks ZERO internal vectored-review status or orchestration narration (no `POOL EXHAUSTED`, `NOT ASSIGNED`, `STOPPED (estimate)`, `coverage-map.md`, `astack-review-ledger`, `Chapman`, `Jackknife`, or narrating which/how many reviewer models ran unless escalating an unconverged risky change in plain language).

FAIL otherwise.
