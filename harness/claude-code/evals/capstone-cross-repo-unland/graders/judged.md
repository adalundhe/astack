---
type: llm
---

Evaluate the cross-repository blast-radius report, safe revert in `repo-core`, pinned release plan, and verification across both repos.

PASS if all of these hold:
- Writes `program/BLAST_RADIUS.md` identifying all three breaking downstream callers in `./repo-service` (`billing.py`, `invoices.py`, `webhooks.py`) with exact `file:line` references and concrete `dict`-vs-`int` `TypeError` failure modes.
- Safely reverts only Commit B in `./repo-core` via a new revert commit without rewriting history (`git reset --hard`) and keeps Commit C's `docs/CHANGELOG.md` and `README.md` intact.
- Updates `program/release-plan.json` to eliminate floating refs, pin exact post-revert 40-char SHAs for `repo-core` and `repo-service`, and order `repo-core` before `repo-service` with `depends_on`.
- Proves both `./repo-core` and `./repo-service` unit test suites pass with clean git trees and intact gates.

FAIL otherwise.
