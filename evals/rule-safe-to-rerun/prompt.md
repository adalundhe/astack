---
description: "In Go mode, fixing a ledger exporter in ./repo routes to safe-to-rerun, makes execution idempotent across repeated runs, writes atomically via temp file and os.replace, cleans up stale temp leftovers, and tests double runs and mid-write crashes."
expected_outcome: "Reads safe-to-rerun/SKILL.md, updates ./repo/src/ledger_exporter.py to converge idempotently by tx_id without duplicates, writes to a same-directory temp file committed via os.replace, cleans stale temp leftovers, preserves the prior target on mid-write crashes, and adds tests for double runs and crash recovery."
timeout_seconds: 360
---

`/astack:go` Fix the ledger exporter in `./repo/src/ledger_exporter.py` (see `./repo/README.md` for the contract). Whenever a batch export is retried after a network hiccup or killed mid-write, the current writer appends duplicate rows or leaves a half-written target file behind. Update `export_entries` so repeated runs converge without duplicates, writes are atomic so crashes never corrupt the existing target file, stale temporary leftovers from crashed runs are cleaned up on rerun, and add tests in `./repo/tests/` proving double-run idempotence and mid-write crash recovery.
