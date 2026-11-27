---
description: "In Go mode, refactoring a batch worker with hardcoded magic constants in ./repo routes to no-picked-constants, replaces arbitrary thresholds with explicit caller config, byte-bounded batching, server Retry-After signals, and runtime adaptation, and tests across configs."
expected_outcome: "Reads no-picked-constants/SKILL.md, removes MAX_BATCH=47, SLEEP_SEC=3.7, and CUTOFF=1234 in ./repo/src/batch_worker.py, bounds batches by explicit payload byte budget, honors caller max_retries and server Retry-After waits, adapts batch bytes to measured latency when target_batch_seconds is set, and tests across configurations."
timeout_seconds: 360
---

`/astack:go` Clean up the batch dispatcher in `./repo/src/batch_worker.py` (see `./repo/README.md` for the contract). The current implementation relies on arbitrary hardcoded numbers (`MAX_BATCH = 47`, `SLEEP_SEC = 3.7`, `CUTOFF = 1234`) that blow memory budgets on large payloads, under-pack small payloads, drop work past 1234 bytes, and ignore upstream `Retry-After` signals. Refactor `BatchWorker` to eliminate those hardcoded thresholds, bound batches by explicit caller-supplied payload byte limits, honor upstream `Retry-After` delays and caller retry budgets, adapt batch byte size at runtime when a latency target is configured, and add tests in `./repo/tests/` verifying behavior across configurations.
