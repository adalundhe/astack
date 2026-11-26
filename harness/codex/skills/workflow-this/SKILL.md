---
name: workflow-this
description: "Turn a reviewed $dagify graph into a crash-resumable automated workflow with explicit task states. Use when planned work should run unattended."
---

# Workflow this

Turn a reviewed `$dagify` task graph into an automated, crash-resumable workflow with explicit task states.

**Skip if one-off.** For single-shot work that needs no unattended execution or recurrence, run the plan directly via `lead` instead of building workflow scaffolding.

1. **Start from a reviewed graph (`dagify`).** Confirm tasks, edges, acceptance criteria, and tests are already verified.
2. **Choose the runner (`automate-this`).** Check `automation.mode` in `~/.config/astack/settings.json` and `astack-tools doctor`:
   - **`agentic-only` (or Python stack absent):** use pure-agentic `lead` flows, the host's native runner, CI, or a repo-language script. Never install Python packages without permission.
   - **`python-stack` (run via `astack-tools python` / `astack-tools werkflow`, saved under `~/.astack/<project_name>/automations/<automation_name>/`):**
     - **taskex** for general automations, background task management, schedules, keep/discard retention, watchers, and checkpointed tasks (can also use `werkflow-modules`; pair with `checkpoint`, `suspend`, `resume`);
     - **orchestral** for shorter, scriptish shell or stdlib-Python DAG waves where step code owns state-passing and conditional logic;
     - **werkflow** for composed `werkflow-modules`, robust implicit state-passing, `WorkflowGroup` pipelines, multi-repo migrations, large-scale refactors, or small-scale CI engines.
3. **Model task states explicitly.** Use `waiting`, `ready`, `running`, `in_review`, `done`, `failed`, and `blocked_on_person` in one transition table, because scattered booleans hide illegal states. A task becomes `ready` only when all dependencies are `done` and reviewed. Diagram the machine (`show-the-states`).
4. **Return typed outcomes.** Emit `done` (with evidence), `failed` (with reason), `inconclusive`, or `blocked` (with the human step), because silent failures corrupt downstream waves. Never hide retries.
5. **Persist per-task state durably.** Store each task's state separately and keep steps idempotent, because crash recovery replays interrupted steps. In Python, use `SQLiteCheckpointStore` with `taskex` or `orchestral`.
6. **Wake on events.** Trigger transitions on completion, review return, or exit status instead of polling loops.
7. **Keep config explicit.** Put measured concurrency, per-role models from `settings.json`, and target environment in one place.
8. **Make execution observable.** Log every state transition with its reason, and expose one status command showing all tasks.
9. **Test the workflow itself:**
   - Validate DAG acyclicity upfront (for `orchestral`, verify `orch.execution_order()`).
   - Kill or pause mid-run and prove checkpoint recovery completes cleanly.
   - Fail one task to confirm dependents skip while independent branches finish.
   - Verify a review block halts downstream steps.
10. **Close cleanly:** when the workflow finishes or fails, run **lookback** to save lessons to `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`. Harden recurring failures via `make-it-stick`.

Only genuine human decisions pause a branch (**decisions-in-plain-words**). Everything else runs to completion or reports failure.

**Done when:** the workflow passes dry-run, failure-isolation, and pause/resume tests, and logs every state transition cleanly.

**Reply:** name the chosen runner, workflow file path, state diagram, verification results, and exact rerun/resume command.

Referenced skills: `taskex` (`../taskex/SKILL.md`), `orchestral` (`../orchestral/SKILL.md`), `werkflow` (`../werkflow/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.
