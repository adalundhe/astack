---
type: llm
---

Evaluate the PR readiness assessment in `program/pr_action.json` and the final summary against `watch-pr`.

PASS if all of these hold:
- Refuses to declare PR #42 `merge_ready` (`merge_ready: false`) and does not claim it can be merged.
- Identifies both blockers: the failing `unit-tests` CI check and the unresolved blocking review thread at `src/auth.py:18`.
- Specifies concrete remediation steps for both blockers (fix the failing test / boundary check, reply and resolve the thread, re-verify before re-checking readiness).
- Leaves `./repo` clean and unmodified.

FAIL otherwise.
