---
type: llm
---

Evaluate the refactored `JobRunner` in `./repo` against `event-driven`.

PASS if all of these hold:
- Removes the `time.sleep` polling loop from `src/job_runner.py`.
- Uses direct completion notifications (`threading.Event` or `concurrent.futures.Future`) so `wait_for` and `wait_all` wake immediately on completion or exception with bounded timeouts.
- Raises `KeyError` immediately for unknown `job_id`s rather than polling until timeout.
- Adds deterministic unit tests verifying immediate notification wakeup, failure propagation, bounded timeouts, and zero `time.sleep` calls.

FAIL otherwise.
