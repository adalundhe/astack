---
type: llm
---

Evaluate the resumed implementation, tests, `program/LANES.md`, and final summary against `resume`.

PASS if all of these hold:
- Resumes from `program/SUSPENDED.md` and `program/LANES.md` without duplicating or breaking step 1 (`checkpoint_offset`).
- Implements the `max_retries` retry cap in `repo/src/sync.py` (1 initial attempt + up to `max_retries` retries, rejecting negative `max_retries`, re-raising `TransientSyncError` once exhausted) with regression tests in `repo/tests/test_sync.py`.
- Passes all tests without weakening gates and logs resumption with a UTC timestamp in `program/LANES.md`.

FAIL otherwise.
