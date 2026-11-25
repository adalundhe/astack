---
type: llm
---

Evaluate the final user-facing report after proactively auditing and hardening `repo/src/vault.py`. Separate objective checks verify all three bugs are fixed and covered by red-first tests.

PASS if the reply clearly summarizes the proven defects found (fail-open malformed token auth, path traversal, and split-lock quota race), how they were fixed and verified, and leaks zero internal review-ledger labels or model rosters.
FAIL otherwise.
