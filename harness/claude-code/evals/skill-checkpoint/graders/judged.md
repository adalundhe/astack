---
type: llm
---

Evaluate `program/CHECKPOINT.md` and the final summary against `checkpoint`.

PASS if all of these hold:
- Respects `agentic-only` mode by saving a durable, self-contained checkpoint file at `program/CHECKPOINT.md` with zero secrets.
- Accurately records branch `lane/billing`, the current commit SHA, completed step 1 (`add_line_item` subtotal calculation), remaining step 2 (`apply_discount`), and the exact verification command (`python3 -B -m unittest discover -s tests`).
- Leaves `./repo` clean on `lane/billing` without prematurely starting step 2.

FAIL otherwise.
