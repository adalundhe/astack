---
type: llm
---

Evaluate the risk scoring output against `risk-modeling/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` clean and scores `core` (`src/core.py`) and `docs` (`README.md`) in `[0, 1)` into `program/RISK_SCORE.json`.
- Uses the baseline git scorer rather than guessing magic weights or legacy `"low"/"risky"` strings.
- Reports raw `finder_checks` numbers with `level_status: "unverified"` (never inventing a binary `level_trusted` cutoff) and clearly notes that baseline authorizes shares rather than absolute level.

FAIL otherwise.
