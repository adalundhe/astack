---
type: llm
---

Evaluate the saved automation under `program/astack_home/nightly-audit/automations/`, usage docs under `program/astack_home/nightly-audit/docs/`, and final response against `workflow-this/SKILL.md`.

PASS if all of these hold:
- Saves a runnable, crash-resumable workflow under `program/astack_home/nightly-audit/automations/<name>/` modeling explicit task states (`waiting`, `ready`, `running`, `in_review`, `done`, `failed`, `blocked_on_person`) with durable per-task state persistence and transition logging.
- Saves usage documentation under `program/astack_home/nightly-audit/docs/` including a state diagram, failure isolation behavior, and exact rerun/resume/status commands.
- Leaves `./repo` untouched and contains zero secrets or internal harness jargon.
- Final response reports the chosen runner, file paths, verification results, and rerun/resume command.

FAIL otherwise.
