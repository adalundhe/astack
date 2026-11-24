---
type: llm
---

The text is the user-facing report of a vectored review on a clean, small, isolated formatting change (`repo/fmt.py`, built by a `haiku` worker, with approved `reviewer_pool` containing `sonnet` and `haiku`). Tool-call and regex graders separately verify that exactly one `astack:reviewer` ran on `sonnet`, zero ran on `haiku` or `general-purpose`, `astack-review-ledger` was run, and zero internal status codes were leaked.

PASS if ALL of the following hold:
- Confirms clearly in plain language that no proven blocking bugs were found in `normalize_spaces` and states what was verified.
- Does NOT leak internal vectored-review status codes or bookkeeping (no `POOL EXHAUSTED`, `NOT ASSIGNED`, `STOPPED (clean single review)`, raw ledger tables, or internal estimator jargon).

FAIL otherwise.
