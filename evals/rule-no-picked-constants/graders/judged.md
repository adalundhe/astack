---
type: llm
---

Evaluate the refactored `BatchWorker` in `./repo` against `no-picked-constants`.

PASS if all of these hold:
- Removes the arbitrary hardcoded constants (`MAX_BATCH = 47`, `SLEEP_SEC = 3.7`, `CUTOFF = 1234`) rather than replacing them with other ungrounded magic numbers.
- Bounds batches by actual payload byte budget supplied explicitly by the caller (`max_batch_bytes`) and honors caller `max_retries`.
- Uses upstream `Retry-After` signals for retry waiting and adapts effective batch byte size at runtime from measured duration when `target_batch_seconds` is configured.
- Adds unit tests verifying behavior across different configurations, payload sizes, retry signals, and runtime adaptation.

FAIL otherwise.
