---
type: llm
---

Evaluate the modularization against `modularize/SKILL.md`.

PASS if all of these hold:
- Cuts `repo/src/monolith.py` along clean domain seams into focused single-purpose modules (parsing, validation, storage formatting) under `repo/src/` with acyclic dependencies.
- Shrinks `repo/src/monolith.py` to a thin orchestrator/facade preserving all public exports (`process_batch`, `parse_batch`, `validate_batch`, `format_ndjson`, `format_summary_tsv`, and error types).
- Keeps `repo/tests/test_monolith.py` passing unchanged without weakening or deleting any tests.
- Includes a clear Mermaid dependency diagram in the response or documentation.

FAIL otherwise.
