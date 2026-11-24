---
type: llm
---

The text is the final report of a vectored review on a concurrency-touching change (`repo/pool.py`, built by a `haiku` worker, with approved `reviewer_pool` containing `sonnet` and `haiku`). Tool-call graders separately verify `astack:reviewer` invocation.

PASS if ALL of the following hold:
- The report opens with a coverage map showing the concurrency vector classified as `risky`.
- At least two reviewers on different approved models from the pool (`sonnet` and `haiku`, including a model other than the worker's `haiku`) ran on the concurrency vector, with per-reviewer verified and dropped counts, overlap/Chapman estimate, and a valid stop status (`STOPPED (estimate)` or `POOL EXHAUSTED`).
- `NOT ASSIGNED`, `POOL EXHAUSTED`, and `COULD NOT TEST` are reported.

FAIL otherwise.
