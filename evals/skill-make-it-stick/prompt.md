---
description: "Fix a recurring naive datetime.now() production regression in src/events.py and add an AST/static structural guard test blocking naive datetime.now() across all src/*.py modules."
expected_outcome: "Reads make-it-stick/SKILL.md, fixes src/events.py to emit UTC-aware timestamps via datetime.now(timezone.utc), adds a structural AST/static regression guard test under repo/tests/ that fails if any src/*.py calls naive datetime.now(), passes unittest, mutation checks on both src/events.py and src/other.py, and gate checks."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/incident.md` describing a recurring production regression in `./repo`.

1. Fix the offending timestamp call in `./repo/src/events.py` so `record_event()` emits a UTC-aware ISO-8601 timestamp (`datetime.now(timezone.utc)`).
2. Make this mistake structurally impossible to reintroduce across `./repo/src/*.py` by adding an automated AST/static regression guard test under `./repo/tests/` that fails whenever any module under `./repo/src/` calls naive `datetime.now()` without a timezone argument.
3. Verify the full test suite passes. (If you also record a durable lesson, store it under `ASTACK_HOME`, never inside `./repo`.)
