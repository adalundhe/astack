---
type: llm
---

Evaluate the git state, `program/LANES.md`, `program/SUSPENDED.md`, and final reply against `suspend`.

PASS if all of these hold:
- Preserves and commits the green WIP edits (`checkpoint_offset` + test) onto branch `lane/sync` so `git status` is clean and unittest passes.
- Appends a UTC-stamped (`YYYY-MM-DDTHH:MMZ`) pause/suspend entry under `## Log` in `program/LANES.md` while keeping the `<!-- astack lane log -->` marker and prior entries intact.
- Writes `program/SUSPENDED.md` recording branch `lane/sync`, the saved commit SHA, paused state, and an exact resume command.

FAIL otherwise.
