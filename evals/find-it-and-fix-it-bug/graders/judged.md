---
type: llm
---

The text is the final report of investigating and fixing wrong invoice totals in `repo/` (`InvoiceProcessor` in `repo/src/processor.py` on `program/billing_events.json`). Separate tool-call and objective post-run verifiers check that `find-it/SKILL.md` and `fix-it/SKILL.md` were read, the 120-event workload matches the oracle, the updated test suite fails on original `main` and passes after the fix, and zero `*_DEBUG_*.*` files remain.

PASS if ALL of the following hold:
- Confirms the bug on the real workload (`program/billing_events.json`) and shrinks the failing case (e.g., to an invalid `retry` followed by a valid `charge`) before/to isolate the root cause cleanly.
- Identifies the root cause accurately: implicit instance flags (`_in_retry` / `_retry_discount_pct`) leaking across events when an invalid retry (`amount_cents <= 0`) returns early.
- Fixes the root cause minimally by eliminating the implicit cross-event state (computing the retry discount directly from the event's `kind` rather than mutating instance flags) without out-of-scope refactoring or narrating fix comments.
- Includes runnable before/after proof (showing the failing case before the fix and passing workload/tests after the fix).

FAIL otherwise.
