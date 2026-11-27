---
type: llm
---

Evaluate the saved workflow under `program/astack_home/data-sync/automations/` and the final response against `orchestral/SKILL.md`.

PASS if all of these hold:
- Saves a self-contained Orchestral multi-wave DAG workflow (`automation.json` with `runner: "orchestral"` plus a valid Python entrypoint using `Orchestral`, `dependencies=[...]`, `orch.execution_order()`, and `SQLiteCheckpointStore`) under `program/astack_home/data-sync/automations/<name>/`.
- Step code explicitly owns state-passing and conditional branching while validating `orch.status == WorkflowStatus.COMPLETED` and per-step `RunStatus.COMPLETE`.
- Leaves `./repo` untouched and leaks zero secrets or internal harness jargon.
- Final response provides exact run and resume commands.

FAIL otherwise.
