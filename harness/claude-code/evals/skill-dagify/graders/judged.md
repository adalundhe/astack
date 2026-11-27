---
type: llm
---

Evaluate `program/DAG.md` against `dagify`.

PASS if all of these hold:
- Leaves `./repo` completely untouched.
- Breaks the 4-module feature (`src/parser.py`, `src/validator.py`, `src/storage.py`, `src/cli.py`) into self-contained tasks that each include `Description`, `Implementation guide`, `Acceptance criteria`, `Tests`, and `Touches`.
- Parallelizes independent upstream tasks (`parser`, `validator`, `storage`) with strictly disjoint writable paths, adding edges only where `cli` genuinely depends on them.
- Includes explicit dependency edges and a valid Mermaid `flowchart` diagram matching the task graph.

FAIL otherwise.
