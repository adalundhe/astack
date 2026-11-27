---
description: "Write a file-and-line-cited walkthrough of the 3-file request pipeline in ./repo (ingest -> transform -> sink), saved under ASTACK_HOME docs with verified citations, ran vs read labels, Mermaid flow diagram, and a worked example while keeping ./repo clean."
expected_outcome: "Reads how-it-works/SKILL.md, inspects and exercises repo/src/ingest.py, repo/src/transform.py, and repo/src/sink.py read-only, saves a walkthrough under program/astack_home/pipe-walk/docs/ with verified file:line citations matching actual function definitions in all 3 files, ran vs read claim markers, a Mermaid flow diagram, and one concrete end-to-end example, leaving ./repo clean."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Explain how the request processing pipeline in `./repo` works end-to-end (`src/ingest.py` -> `src/transform.py` -> `src/sink.py`) for project `pipe-walk` (`ASTACK_HOME=./program/astack_home`).

Explore read-only, verify key runtime behavior by executing code or tests, label claims as **ran** vs. **read**, cite exact `file:line` locations for every stage across all three modules, include a Mermaid flow diagram plus one concrete walked example, and persist the walkthrough under `$ASTACK_HOME/pipe-walk/docs/`. Leave `./repo` untouched.
