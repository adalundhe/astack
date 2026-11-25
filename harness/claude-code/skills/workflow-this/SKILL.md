---
name: workflow-this
description: "Turn a /dagify task graph into a self-running, crash-resumable workflow (using taskex, orchestral, werkflow, CI, or native runners) with explicit task states and typed outcomes. Use when planned work should run or recur unattended."
disable-model-invocation: true
---

# Workflow this

Turn a reviewed `/dagify` graph into an automated, crash-resumable workflow with explicit task states.

1. **Start from a reviewed graph (**dagify**):** tasks, edges, acceptance criteria, and tests are already verified.
2. **Choose the runner (**automate-this**):** check `automation.mode` in `~/.config/astack/settings.json` (**setup**) and `astack-tools doctor`:
   - **`agentic-only` (or Python stack absent):** use pure-agentic flows (**lead**), the host's native runner, CI, or a repo-language script. Never install Python packages without permission.
   - **`python-stack` (run via `astack-tools python` / `astack-tools werkflow`):**
     - **taskex** (+ **checkpoint**, **suspend**, **resume**) for checkpointed tasks, shell watchers, and live pause/resume;
     - **orchestral** (+ **checkpoint**, **suspend**, **resume**) for DAG waves, cycle checks, branch skipping, and SQLite wave recovery;
     - **werkflow** for `@step` data injection, `.werkflow.json`/prompts, or `werkflow-modules` integrations.
3. **Model task states explicitly (**no-implicit-states**):** `waiting`, `ready`, `running`, `in_review`, `done`, `failed`, `blocked_on_person`, with all transitions in one place. A task becomes `ready` only when all dependencies are `done` and reviewed. Diagram the machine (**show-the-states**).
4. **Return typed outcomes (**no-hidden-flow-control**):** `done` (with evidence), `failed` (with reason), `inconclusive`, or `blocked` (with the human step). No silent failures or hidden retries.
5. **Persist per-task state durably:** store each task's state separately (**no-shared-writes**) and make every step idempotent (**safe-to-rerun**). In Python, use `SQLiteCheckpointStore` with `taskex` or `orchestral`.
6. **Wake on events (**event-driven**):** trigger transitions on task completion, review return, or exit status instead of polling loops.
7. **Keep config explicit (**no-hidden-config**):** set measured concurrency, per-role models from `settings.json`, and target environment in one place.
8. **Make execution observable:** log every state transition with reason, and expose one status command showing all tasks.
9. **Test the workflow itself (**prove-it**, **tests-assert-behaviour**):** validate DAG acyclicity upfront (`execution_order()`), kill or pause mid-run to verify checkpoint resume, fail one task to confirm dependents skip while independent branches continue, and verify review blocks halt downstream steps.
10. **Close with **lookback**:** when the workflow finishes or fails, run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` and harden recurring failures via **make-it-stick**.

Only genuine human decisions pause a branch (**decisions-in-plain-words**); everything else runs to completion or reports failure.

Referenced skills: `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `automate-this` (`${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`), `setup` (`${CLAUDE_SKILL_DIR}/../setup/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `taskex` (`${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`), `checkpoint` (`${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`), `suspend` (`${CLAUDE_SKILL_DIR}/../suspend/SKILL.md`), `resume` (`${CLAUDE_SKILL_DIR}/../resume/SKILL.md`), `orchestral` (`${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`), `werkflow` (`${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`), `no-implicit-states` (`${CLAUDE_SKILL_DIR}/../no-implicit-states/SKILL.md`), `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`), `no-hidden-flow-control` (`${CLAUDE_SKILL_DIR}/../no-hidden-flow-control/SKILL.md`), `no-shared-writes` (`${CLAUDE_SKILL_DIR}/../no-shared-writes/SKILL.md`), `safe-to-rerun` (`${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md`), `event-driven` (`${CLAUDE_SKILL_DIR}/../event-driven/SKILL.md`), `no-hidden-config` (`${CLAUDE_SKILL_DIR}/../no-hidden-config/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `tests-assert-behaviour` (`${CLAUDE_SKILL_DIR}/../tests-assert-behaviour/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `make-it-stick` (`${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.
