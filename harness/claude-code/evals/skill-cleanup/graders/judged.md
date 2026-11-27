---
type: llm
---

Evaluate the cleanup outcome and final reply against `cleanup`.

PASS if all of these hold:
- Removes the 3 temporary scratch files inside `./repo` (`debug_tmp.log`, `scratch_repro.py`, `.tmp_trace`) by exact path without touching tracked source or test files.
- Strictly preserves both durable bundles under `program/astack_home/billing/` (`reviews/2026-11-25T10-00-00Z/proof.txt` and `repros/repro_bug.py`).
- Verifies `git status` is clean and unit tests still pass, and lists what was removed and kept.

FAIL otherwise.
