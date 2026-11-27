---
description: "Turns a cryptic, traceback-prone CLI with a destructive default into a consumer-friendly CLI with actionable errors, empty-state handling, visible feedback, and safe defaults."
expected_outcome: "Reads delight-users/SKILL.md, eliminates raw tracebacks and 'Error 42', adds actionable error messages with next steps, clear empty-state handling, visible action feedback, a safe non-destructive default for clean, and CLI behavior tests."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Users are reporting rough edges with the task tracker CLI in `./repo/src/taskcli.py` (invoked as `python3 src/taskcli.py --store <file> <command>`):
- Running `list` before any store file exists or calling `add`/`done` with missing or bad arguments crashes with raw Python tracebacks.
- Completing an unknown task ID prints `"Error 42"` without saying what failed or what to run next.
- Listing an empty task store prints nothing at all, and `add`/`done` give no confirmation output.
- Running `clean` deletes open tasks too by default unless an opt-in flag is supplied, causing accidental data loss.

Improve `./repo/src/taskcli.py` across normal, empty, and failure flows with clear actionable messages and safe defaults, and expand `./repo/tests/test_taskcli.py` to test those CLI behaviors.
