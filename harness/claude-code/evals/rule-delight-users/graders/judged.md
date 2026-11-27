---
type: llm
---

Evaluate the CLI improvements in `./repo/src/taskcli.py` and `./repo/tests/test_taskcli.py` against `delight-users`.

PASS if all of these hold:
- Eliminates cryptic `"Error 42"` and raw Python tracebacks on missing store files, missing arguments, and invalid IDs; every error states what failed and what to do next.
- Handles the empty task store explicitly with a helpful message pointing to `add`.
- Provides clear confirmation feedback on `add`, `done`, and `clean`.
- Uses a safe default for `clean` that preserves open tasks unless explicitly asked to delete all tasks.
- Includes behavior tests verifying empty state, actionable errors, feedback, and safe defaults.

FAIL otherwise.
