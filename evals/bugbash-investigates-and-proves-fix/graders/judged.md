---
type: llm
---

The text is the lead's **user-facing** final reply after resolving the customer bug reported in `program/bug-report.md` (with linked `program/linked-spec.md` and `program/incident-trace.log`) against `repo/` (`TransferLedger` / `ResultCache`) and writing `program/pr-body.md`. Separate tool-call, regex, and `verify.py` graders objectively check internal workflow execution (`bugbash/SKILL.md` read, `astack:reviewer` and `astack:worker` spawns, zero `general-purpose` calls, red-first tests, both bugs fixed, clean `program/pr-body.md`, zero debug leftovers). Do **not** require internal review-orchestration narration (model rosters, reviewer round counts, or internal ledger bookkeeping) in this user-facing reply—`review` forbids leaking those.

PASS if ALL of the following hold:
- Explains both proven root causes accurately with reference to the spec/incident facts: cache keys were not tenant-scoped (`(tenant_id, idempotency_key)`), and transient `status == "error"` results were cached so retries stayed stuck failing.
- Summarizes the minimal fix and confirms same-tenant duplicate replay still returns the cached `ok` receipt without double-charging.
- Summarizes concrete runnable before/after verification proof and points to `program/pr-body.md` containing the PR verification evidence.
- Writes clearly and concisely in plain English without leaking internal review-ledger labels, estimator formulas, model rosters, or process bookkeeping.

FAIL otherwise.
