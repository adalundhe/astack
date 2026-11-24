---
type: llm
---

Evaluate whether the session routed the review through astack's dedicated reviewer agent.

PASS if:
- The session spawned `astack:reviewer` (not `general-purpose`) and reported the resulting verdict/findings concisely.

FAIL otherwise.
