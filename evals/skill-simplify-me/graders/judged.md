---
type: llm
---

Evaluate the simplification of `repo/src/report.py` against `simplify-me/SKILL.md`.

PASS if all of these hold:
- Removes the 5 unnecessary ceremony layers (`ConfigAdapter`, `AbstractBaseFormatter`, `StrategyRegistry`, `FormatterFactory`, `FormatterProxyWrapper`) and narrating comments from `repo/src/report.py`, replacing them with concise, direct stdlib Python.
- Preserves 100% of external behavior (`render_report` for CSV with/without header, quoting, empty rows, sorted JSON, case-insensitive format handling, and `ValueError` on unknown formats).
- Keeps `repo/tests/test_report.py` green without deleting or weakening tests, and summarizes clearly what was cut and what was kept.

FAIL otherwise.
