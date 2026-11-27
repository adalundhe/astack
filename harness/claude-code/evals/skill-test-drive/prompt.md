---
description: "Atomic outcome eval for test-drive: writes an executable end-to-end CLI driver script for repo/src/todo_cli.py exercising add, list, complete, and invalid-ID flows, fixes the uncaught KeyError bug on missing IDs, adds regression tests, and passes mutation + gate checks."
expected_outcome: "Reads test-drive/SKILL.md, creates an executable driver script (program/drive-todo.py or repo/scripts/drive_todo.py) driving add/list/complete/invalid-ID end-to-end against repo/src/todo_cli.py, fixes the missing-ID KeyError crash in repo/src/todo_cli.py to exit non-zero cleanly without a traceback, adds unittest regression coverage in repo/tests/, and passes driver execution, unittest, mutation, and gate checks."
timeout_seconds: 480
---

`/astack:go` `./repo` contains a runnable Python CLI app (`src/todo_cli.py`) with no end-to-end verification driver yet. Test-drive the real CLI end-to-end across its user flows (`add`, `list`, `complete`, and completing an invalid/missing todo ID): write an executable driver script at `program/drive-todo.py` (or `repo/scripts/drive_todo.py`) that runs those real CLI flows in an isolated data directory, fix any broken user-flow bug you uncover in `./repo/src/todo_cli.py`, add regression unit tests under `./repo/tests/`, and prove both the driver script and test suite pass.
