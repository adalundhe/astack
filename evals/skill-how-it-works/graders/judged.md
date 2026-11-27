---
type: llm
---

Evaluate the pipeline walkthrough against `how-it-works/SKILL.md`.

PASS if all of these hold:
- Persists an accurate walkthrough under `program/astack_home/pipe-walk/docs/` without editing `./repo`.
- Cites verified `file:line` locations for real functions across all three files (`src/ingest.py`, `src/transform.py`, `src/sink.py`).
- Labels claims explicitly as **ran** (e.g., running unit tests or `run_pipeline`) vs. **read** (static source inspection).
- Includes a Mermaid flow diagram and walks one concrete end-to-end input/output example.

FAIL otherwise.
