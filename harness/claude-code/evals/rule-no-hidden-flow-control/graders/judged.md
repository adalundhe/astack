---
type: llm
---

Evaluate the fixed profile loader in `./repo` against `no-hidden-flow-control`.

PASS if all of these hold:
- Removes the broad `except Exception: return None` catch-all in `src/profile_loader.py`.
- Catches only specific expected exceptions (`FileNotFoundError`, `json.JSONDecodeError`, `KeyError`, `ValueError`/`TypeError`) narrowly around the raising operations.
- Returns explicit typed result/error values instead of `None` for expected failures while letting unexpected errors and interrupts propagate.
- Adds unit tests exercising each distinct failure value and unexpected-error propagation.

FAIL otherwise.
