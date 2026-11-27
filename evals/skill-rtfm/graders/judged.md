---
type: llm
---

Evaluate the answer against `rtfm/SKILL.md`.

PASS if all of these hold:
- Directly answers why `MAX_RETRIES = 3` in `src/retry.py`: the upstream API enforces a strict 429 ban on the 4th attempt (15-minute IP lockout).
- Explicitly cites both `docs/AD-007.md` and the exact git commit SHA that lowered `MAX_RETRIES` from 5 to 3.
- Clearly states there is no need to ask the author because the decision is already settled in docs and commit history.
- Leaves `./repo` untouched.

FAIL otherwise.
