---
type: llm
---

Evaluate the fixed Python code against `no-hidden-flow-control`.

PASS if all of these hold:
- Removes the broad `except Exception: return None` catch-all.
- Catches only specific expected exceptions (e.g. `FileNotFoundError`/`OSError`, `json.JSONDecodeError`, `KeyError`/`ValueError`/`TypeError`) narrowly around the exact operations that raise them.
- Returns explicit typed result/error values instead of silently returning `None` for all failures.
- Lets unexpected programming errors and interrupts propagate rather than swallowing them.
- Includes tests exercising each distinct failure value.

FAIL otherwise.
