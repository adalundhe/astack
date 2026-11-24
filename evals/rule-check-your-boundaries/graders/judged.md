---
type: llm
---

Evaluate the refactored Python code against `check-your-boundaries`.

PASS if all of these hold:
- Parses and validates the raw request payload once at the boundary into explicit typed domain values (e.g. dataclasses / typed structures), returning a typed error or clear boundary failure for invalid input.
- Core logic functions (`calculate_total`, `apply_discount` or equivalent) accept the parsed domain types rather than raw `dict` or `http_request` objects.
- Removes redundant defensive `isinstance` / `None` / key-existence re-validation inside core logic.

FAIL otherwise.
