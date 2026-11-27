---
type: llm
---

Evaluate the changes in `./repo` and the final summary against `fail-safely`.

PASS if all of these hold:
- `UpstreamClient` passes explicit finite timeouts to the transport on both `fetch` and `submit`.
- `fetch` bounds retries with exponential backoff, jitter, and a shared retry budget; `submit` does not retry non-idempotent POST failures.
- `HealthService.liveness` checks only process liveness without querying the DB, while `readiness` bounds DB ping wait time and reports `not_ready` on failure or timeout.
- Unit tests exercise injected faults (timeouts, 5xx bursts, budget exhaustion, non-idempotent POST failure, and slow/failing DB probes) and pass.

FAIL otherwise.
