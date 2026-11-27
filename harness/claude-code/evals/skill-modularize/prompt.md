---
description: "Atomic outcome eval for modularize: splits a 180-line tangled repo/src/monolith.py into focused single-purpose modules (parser, validator, storage) while keeping public entrypoints and repo/tests/test_monolith.py green, acyclic imports, measurable shrinkage, and passing mutation + gate checks."
expected_outcome: "Reads modularize/SKILL.md, extracts clean single-responsibility modules under repo/src/ (such as parser.py, validator.py, storage.py) with acyclic dependencies, trims repo/src/monolith.py to a slim entrypoint preserving all public exports, keeps repo/tests/test_monolith.py 100% green without weakening gates, passes resilient mutation checks on both monolith and extracted modules, and includes a Mermaid dependency diagram."
timeout_seconds: 420
---

`/astack:go` `./repo/src/monolith.py` currently mixes raw batch parsing, domain validation, and storage formatting in one ~185-line tangled file, pinned by `./repo/tests/test_monolith.py`. Modularize `./repo/src/monolith.py` into focused, single-purpose modules under `./repo/src/` (e.g. `parser.py`, `validator.py`, `storage.py`) with acyclic dependencies, keeping all public entrypoints in `src/monolith.py` and all tests in `./repo/tests/test_monolith.py` passing unchanged. Include a brief Mermaid dependency diagram in your summary.
