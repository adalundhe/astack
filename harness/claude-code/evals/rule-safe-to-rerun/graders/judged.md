---
type: llm
---

Evaluate the implementation and test plan against `safe-to-rerun`.

PASS if all of these hold:
- Reads current state first and converges (does not append duplicate `feature=<name>` entries if already present).
- Writes to a temporary file in the same directory and atomically renames (`os.replace`) into place rather than writing in place.
- Cleans up or makes temporary/lock leftovers identifiable as stale if a previous run crashed.
- Describes testing both running the operation twice in a row and interrupting/crashing mid-run followed by a rerun to verify the final state.

FAIL otherwise.
