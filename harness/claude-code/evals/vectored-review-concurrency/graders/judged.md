---
type: llm
---

The text is the user-facing report of a vectored review on a concurrency-touching change (`repo/pool.py` `JobPool.drain_batch`, built by a `haiku` worker, with approved `reviewer_pool` containing `sonnet` and `haiku`). Tool-call and regex graders separately verify `astack:reviewer` spawns on both `sonnet` and `haiku`, `astack-review-ledger` execution, zero `general-purpose` calls, and zero leaked internal status tokens.

PASS if ALL of the following hold:
- Reports the proven blocking concurrency bug in `JobPool.drain_batch` (split lock acquisitions between slicing and deleting items causing duplicate drains / lost items / corrupted `drained` count) with concrete reproduction and evidence.
- Relays only proven, high-signal issues in plain language without dumping internal vectored-review status labels (`POOL EXHAUSTED`, `NOT ASSIGNED`, raw capture–recapture formulas, or internal pool bookkeeping).
- Because a 2-reviewer pool cannot satisfy the cautious stopping bound when blocking bugs are found, clearly indicates that landing should wait until the proven bug is fixed and either more reviewers are approved or the user accepts the risk, stating likely remaining blocking bugs with a range in plain words.

FAIL otherwise.
