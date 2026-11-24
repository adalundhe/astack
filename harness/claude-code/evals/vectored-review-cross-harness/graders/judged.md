---
type: llm
---

The text is the user-facing report of a cross-harness vectored review on a high-risk auth/security change (`repo/auth.py` on branch `lane/token-refresh`, which skips expiry checks on refreshed tokens `tag == "r"` and compares HMAC digests with `!=` instead of `hmac.compare_digest`), using the multi-harness `reviewer_pool` in `program/settings.json`. Tool-call and regex graders separately verify `astack-dispatch`, `astack-review-ledger`, zero `general-purpose` calls, and zero leaked internal status codes.

PASS if ALL of the following hold:
- Reports at least one proven blocking auth/security bug (e.g. expired refreshed tokens accepted forever, or non-constant-time HMAC comparison) with concrete reproduction and evidence.
- Because the risky review could not converge across all approved models (or if a cross-harness model was unreachable), clearly states in plain language that landing should wait for a human decision (approve more models or accept the risk) without leaking internal ledger jargon (`POOL EXHAUSTED`, `NOT ASSIGNED`, `STOPPED (estimate)`, or raw ledger tables).

FAIL otherwise.
