---
type: llm
---

Evaluate the saved automation under `program/astack_home/ops-portal/automations/` and the final response against `taskex/SKILL.md`.

PASS if all of these hold:
- Saves a self-contained TaskEx health-check watcher (`automation.json` with `runner: "taskex"` plus a valid Python entrypoint using `TaskRunner`, `RunStatus`, `SQLiteCheckpointStore`, and `shell=False`) under `program/astack_home/ops-portal/automations/<name>/`.
- Supports bounded `--once` / `--dry-run` / `--resume` / `--clear-checkpoints` operation and checks `RunStatus.COMPLETE` explicitly.
- Leaves `./repo` untouched and contains zero hardcoded secrets.
- Final response provides exact run and resume commands without leaking internal harness jargon.

FAIL otherwise.
