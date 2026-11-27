---
description: "Atomic outcome eval for dagify: slices a 4-module feature spec for ./repo into program/DAG.md with per-task required fields, strictly disjoint writable paths for parallel tasks, explicit dependency edges, and a valid Mermaid flowchart, leaving ./repo clean."
expected_outcome: "Reads dagify/SKILL.md, inspects ./repo and program/spec.md without editing ./repo, writes program/DAG.md covering src/parser.py, src/validator.py, src/storage.py, and src/cli.py with Description, Implementation guide, Acceptance criteria, Tests, Touches (disjoint for parallel tasks), explicit edges, and a Mermaid flowchart."
timeout_seconds: 360
---

`/astack:go` Turn the multi-module feature spec in `program/spec.md` for `./repo` (`src/parser.py`, `src/validator.py`, `src/storage.py`, `src/cli.py`) into an execution graph saved at `program/DAG.md`. Include every required task field, keep writable paths strictly disjoint across parallel tasks, list explicit dependency edges, and include a Mermaid flowchart diagram. Do not edit `./repo` yet.
