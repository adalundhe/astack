---
description: "Remove redundant unmeasured balance/summary caches and global state from a billing ledger so balances derive directly from the single source of truth."
expected_outcome: "Reads minimize-state-stores/SKILL.md, removes _balance_cache, _summary_cache, and module-level global cache from src/ledger.py, derives balances and summaries on demand from ledger entries, and adds tests proving accuracy across charges, refunds, adjustments, voids, and separate ledger instances."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Customers see stale account balances and summaries in `./repo` (`src/ledger.py`) after refunds, adjustments, and voided entries, and separate ledger instances bleed balances into each other.

Read `./repo/README.md` for the ledger rules and public API. Eliminate the redundant unmeasured caches and shared global state in `./repo/src/ledger.py` so every balance and summary is derived directly from the primary ledger entries, add unit tests under `./repo/tests/` covering refund/adjustment/void sequences and instance isolation, and verify all tests pass.
