---
type: llm
---

Evaluate whether the session delegated the implementation task to astack's dedicated worker agent.

PASS if:
- The session spawned `astack:worker` (not `general-purpose`) with both a Deliverable and a Done when check, and reported the outcome.

FAIL otherwise.
