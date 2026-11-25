---
type: llm
---

The text is the lead's final reply after running a bugbash on `program/bug-report.md` (with linked `program/linked-spec.md` and `program/incident-trace.log`) against `repo/` (`TransferLedger` and `ResultCache`) and writing `program/pr-body.md`. Separate tool-call, regex, and objective post-run verifiers check `bugbash/SKILL.md` read, `astack:reviewer` (`>=3`) and `astack:worker` (`>=1`) spawns, zero `general-purpose` spawns, zero internal ledger leaks, both bugs fixed with red-first tests, and `program/pr-body.md` created cleanly.

PASS if ALL of the following hold:
- Fetches and uses the linked spec (`program/linked-spec.md`) and trace (`program/incident-trace.log`) in both the investigation swarm and post-fix review.
- Runs read-only investigation reviewers using `find-it` (without modifying the repo under review; testing any candidate fix only in isolated Slates VFS volumes or throwaway scratch worktrees) and peer `challenge` (logging rejected theories as `decided:` entries) before dispatching the worker with `fix-it` in an isolated Slates VFS volume or git worktree.
- Passes the original bug report, linked docs, and any rejected theories (`decided:` entries) / failed fix attempts to post-fix reviewers instructed to use `prove-it`, confirms the fix covers BOTH root causes (tenant-scoped `(tenant_id, idempotency_key)` cache keys AND not caching `status == "error"` results) without breaking same-tenant duplicate replay, and folds fixes/rejected theories/failed attempts into durable lessons via `make-it-stick`.
- Summarizes and attaches runnable before/after verification proof and evidence in `program/pr-body.md` cleanly with zero leaked internal review bookkeeping.

FAIL otherwise.
