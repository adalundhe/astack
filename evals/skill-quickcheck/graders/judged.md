---
type: llm
---

Evaluate the quickcheck output against `quickcheck/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` completely clean (read-only check) and writes the findings to `program/QUICKCHECK.md`.
- Performs a single focused check without splitting into vectored review waves or running `astack-review-ledger`.
- Catches and proves the real blocking regression in `src/cache.py`: updating an existing key in `Cache.put` appends a duplicate entry to `_order`, causing premature eviction of live entries and violating `docs/ARCHITECTURE.md` (AD-001).
- Does NOT raise blocking issues for user-clarified or documented choices (FIFO instead of LRU, single-threaded design without locks, or `DATA_DIR` defaulting to `./var/data` as documented in `README.md` and `scripts/run.sh`).

FAIL otherwise.
