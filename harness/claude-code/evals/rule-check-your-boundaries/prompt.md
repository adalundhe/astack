---
description: "In Go mode, refactoring a raw-dict webhook processor in ./repo routes to check-your-boundaries, parses and validates payloads once at the entry point into typed domain dataclasses, and tests malformed inputs."
expected_outcome: "Reads check-your-boundaries/SKILL.md, parses raw webhook payloads once at the entry point into typed domain dataclasses, strips scattered dict re-checks from core helpers, rejects malformed inputs at the boundary, and adds passing unit tests."
timeout_seconds: 360
---

`/astack:go` Clean up the Python webhook invoice processor in `./repo` (`./repo/src/webhooks.py`; see `./repo/README.md` for the contract). Right now raw payloads get passed deep into helper functions, defensive dict checks are duplicated everywhere, and malformed requests either slip through or crash with unhandled errors. Refactor `./repo/src/webhooks.py` so incoming payloads are parsed and validated once at the entry point into typed domain objects, keep core calculation helpers operating directly on those typed objects, and add thorough tests in `./repo/tests/` covering both valid and malformed payloads.
