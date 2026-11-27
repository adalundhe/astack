---
type: llm
---

Evaluate the test-drive workflow and fix against `test-drive/SKILL.md`.

PASS if all of these hold:
- Ships an executable end-to-end driver script (`program/drive-todo.py` or `repo/scripts/drive_todo.py`) that drives `repo/src/todo_cli.py` in an isolated data directory across `add`, `list`, `complete`, and invalid/missing ID user flows and exits 0.
- Fixes the uncaught `KeyError` crash on `complete <missing_id>` in `repo/src/todo_cli.py` so missing IDs print a clear error message and exit non-zero without a Python traceback.
- Adds regression unit tests in `repo/tests/` proving both successful completion and clean handling of missing IDs, without weakening or skipping existing tests.

FAIL otherwise.
