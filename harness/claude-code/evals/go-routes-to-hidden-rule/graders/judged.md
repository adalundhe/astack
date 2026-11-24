---
type: llm
---

Evaluate the review of `wait_for_job`.

PASS if all of these hold:
- Identifies the fixed `time.sleep(2)` polling loop as violating `event-driven` (and the hardcoded `2` seconds as a picked constant if `no-picked-constants` is noted).
- Recommends waking directly on a completion event (webhook, callback, notification, condition/future, or server push) or, if the external client cannot provide events, polling only at its documented rate/signal rather than an arbitrary sleep.

FAIL otherwise.
