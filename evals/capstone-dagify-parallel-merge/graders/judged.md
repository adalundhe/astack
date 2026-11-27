---
type: llm
---

Evaluate the DAG plan, branch consolidation, parallel lane integration onto `main`, and closing lesson capture.

PASS if all of these hold:
- Writes `program/DAG.md` with an acyclic Mermaid `flowchart` and per-task sections (`Description`, `Implementation guide`, `Acceptance criteria`, `Tests`, `Touches`) enforcing disjoint writable file ownership for parallel lanes.
- Consolidates the 4 noisy WIP commits on `lane/parser` down to 1–2 commits with identical tree contents while preserving authorship credit for `Alice <alice@example.invalid>`.
- Integrates both `lane/parser` and `lane/formatter` onto `main`, wires `src/pipeline.py` with passing unit tests, leaves `main` clean, and preserves gates.
- Records a valid active `LESSON.md` with flat YAML frontmatter and all required sections under `program/astack_home/reports/lessons/`, with zero lesson files inside `./repo`.

FAIL otherwise.
