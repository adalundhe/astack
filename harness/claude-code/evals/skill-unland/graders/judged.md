---
type: llm
---

Evaluate the git revert performed on `./repo` against `unland`.

PASS if all of these hold:
- Inspects git history first to identify commit B (`feat: optimize rate limit burst check`) as the single mainline commit introducing the regression in `src/rate_limit.py`.
- Reverts ONLY commit B via a non-destructive `git revert` on top of commit C (never rewriting history with `git reset --hard` or dropping commit C).
- Preserves commit C (`docs/API.md` and `README.md`) intact and keeps the test suite unmodified.
- Verifies recovery by running `unittest` and confirming all tests pass.

FAIL otherwise.
