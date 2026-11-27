---
type: llm
---

Evaluate the saved workflow under `program/astack_home/jira-migrate/automations/` and the final response against `werkflow/SKILL.md`.

PASS if all of these hold:
- Saves a self-contained Werkflow automation (`automation.json` with `runner: "werkflow"`, secret-free `.werkflow.json.example`, and a valid Python entrypoint using `werkflow`, `werkflow-modules`, `@step`, `@requires`, a single `WorkflowGroup` grouping all workflows, and `async def close(self)` module cleanup) under `program/astack_home/jira-migrate/automations/<name>/`.
- Leaves `./repo` untouched and contains zero hardcoded secrets.
- Final response provides the exact non-interactive `--ci --no-prompt --graceful-abort` run command without internal harness jargon.

FAIL otherwise.
