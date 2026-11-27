---
type: llm
---

Evaluate the redesigned `RouteScheduler` in `./repo` against `data-structures-first`.

PASS if all of these hold:
- Replaces the nested dict-of-lists-of-tuples and parallel worker arrays (`_worker_names`, `_worker_capacities`, `_worker_loads`) with typed domain records (`Route` / `Worker` dataclasses) and integer `cost_cents` (no float money arithmetic).
- Maintains a single canonical store with consistent indexed lookups (by route ID, worker ID, and region) so invariants hold across add, reassign, remove, and unregister without O(n^2) scans.
- Adds unit tests verifying correctness, capacity enforcement, reassignment load conservation, duplicate rejection, tie-breaking, and exact integer cost totals.

FAIL otherwise.
