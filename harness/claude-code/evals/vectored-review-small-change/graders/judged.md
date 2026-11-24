---
type: llm
---

The text is the final report of a vectored review on a small, isolated formatting change (`repo/fmt.py`, built by a `haiku` worker, with approved `reviewer_pool` containing `sonnet` and `haiku`). Tool-call graders separately verify `astack:reviewer` invocation.

PASS if ALL of the following hold:
- The report opens with a coverage map showing the vector classified as `low` risk.
- Only **one** reviewer ran on a model from the approved pool other than the worker's (`sonnet`), with verified and dropped counts, and stopped cleanly (`STOPPED (clean single review)`) without spawning a second reviewer (or added a second model via `astack-review-ledger` only if a verified bug was reported).
- `NOT ASSIGNED`, `POOL EXHAUSTED`, and `COULD NOT TEST` are reported.

FAIL otherwise.
