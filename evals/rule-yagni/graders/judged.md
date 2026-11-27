---
type: llm
---

Evaluate the legacy-code removal and caller migration against `yagni`.

PASS if all of these hold:
- Migrated all callers (`./repo/src/importer.py` and `./repo/src/report.py`) directly to `parse_csv`.
- Deleted `parse_v1`, `parse_records`, `ENABLE_LEGACY_MODE`, and the unused `legacy_compat` parameter from `./repo/src/parser.py` in the same change.
- Replaced retired-path tests in `./repo/tests/test_pipeline.py` with tests covering consumers on `parse_csv`, including quoted CSV fields.
- Zero references to legacy symbols remain in `src/` or `tests/`.

FAIL otherwise.
