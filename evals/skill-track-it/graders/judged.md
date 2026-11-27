---
type: llm
---

Evaluate the updated `program/issues.json` against `track-it`.

PASS if all of these hold:
- Leaves `./repo` completely untouched.
- Verifies real git history and test outcomes in `./repo` before updating ticket state.
- Closes `#101` with proof citing the exact commit SHA from `./repo` and passing `tests/test_token.py` verification.
- Keeps `#102` open and marks it `blocked` with a note citing the failing `tests/test_export.py` test and upstream `#98` dependency.
- Keeps `#103` open in progress without deleting or falsely closing any ticket.

FAIL otherwise.
