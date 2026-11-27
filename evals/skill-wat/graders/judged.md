---
type: llm
---

Evaluate the rewritten status summary against `wat/SKILL.md`.

PASS if all of these hold:
- Leads immediately with the blocking bug and decision: do not ship release v2.4 because an `orders` table race condition causes double-charges on concurrent checkout retries.
- Gives the concrete next action (add a row lock or unique idempotency constraint in `src/orders.py` and re-test).
- Preserves all key measured staging facts (`3 of 12` concurrent retry requests produced duplicate charges; `p95` latency `180ms`; release `v2.4`).
- Strips 100% of internal process narration, task IDs, worktree paths, bare commit hashes, rule tags, and review-ledger state.
- Leaves `./repo` clean.

FAIL otherwise.
