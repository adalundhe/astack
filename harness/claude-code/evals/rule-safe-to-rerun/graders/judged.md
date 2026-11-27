---
type: llm
---

Evaluate the fixed ledger exporter in `./repo` against `safe-to-rerun`.

PASS if all of these hold:
- Converges from existing state keyed by `tx_id` so repeated or overlapping runs produce deterministic output with zero duplicate rows.
- Writes to a temporary file in the same directory, flushes/fsyncs, and commits atomically via `os.replace` rather than writing in place.
- Cleans up incomplete temp files on crash and sweeps stale temporary leftovers on rerun, leaving the prior target file untouched if a write fails midway.
- Adds unit tests proving double-run idempotence and mid-write crash recovery.

FAIL otherwise.
