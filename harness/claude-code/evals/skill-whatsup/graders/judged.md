---
type: llm
---

Evaluate the catch-up summary against `whatsup`.

PASS if all of these hold:
- Reports all three planted facts accurately from disk and git:
  1. `lane/parser` merged at its exact commit SHA.
  2. `lane/cache` is blocked on the missing `cache_ttl_seconds` schema key (waiting on human choice).
  3. Settled decision: SQLite WAL mode for local persistence.
- Organizes the brief concisely in plain language without internal orchestration jargon.
- Stays strictly read-only on `./repo`.

FAIL otherwise.
