---
name: resume
description: "Unpause live taskex/orchestral runs or recover crashed runs from SQLite checkpoints without duplicates. Use when unpausing or restarting interrupted Python automation."
disable-model-invocation: true
---

# Resume

Unpause live `PAUSED` runs in place, or recover failed, cancelled, and crashed `taskex` / `orchestral` runs from checkpoints. Scope: Python `taskex`/`orchestral` automation only; use `whatsup` for agentic sessions, and atomic files/commits under `agentic-only`.

## 1. Choose live unpause vs. checkpoint recovery

- **Live unpause (same runner, `PAUSED`):** continues in place and unfreezes timeouts. Prefer this while the process is alive because in-memory state stays intact.
- **Checkpoint replay (failed, cancelled, or fresh process):** loads `SQLiteCheckpointStore` state so completed steps skip and incomplete steps read `last_checkpoint()`. Use after crashes because process memory is gone.

## 2. Resume `taskex` runs and schedules

- **Live unpause:**
  - Single run: `run = await runner.resume(token)` returns the same `Run` and sends `SIGCONT` to paused POSIX process groups.
  - Recurring schedule: `await runner.resume_schedule(token)` unpauses both the active run and schedule loop.
- **Restart-from-checkpoint recovery:**
  1. Inspect saved progress first: `cp = await runner.get_checkpoint(old_token)` or `await runner.get_latest_task_checkpoint("etl")`.
  2. Same runner (task registered): `new_run = await runner.resume(old_token)`.
  3. Fresh process / `TaskRunner` sharing the same `SQLiteCheckpointStore`:
     ```python
     with SQLiteCheckpointStore("./state/checkpoints.db") as store:
         async with TaskRunner(config=Env(MERCURY_SYNC_EXECUTOR_TYPE="none"), checkpoint_store=store) as runner:
             new_run = await runner.resume(old_token, *args, call=process_items, **kwargs)
             # Or seed directly: runner.run(process_items, *args, alias="etl", resume_from=cp)
             res = await runner.wait(new_run.token)
     ```
  - **Async store gotcha (`taskex`):** use `await runner.resume(...)` or pass an awaited `Checkpoint` to `resume_from=`. Passing a string token to sync `runner.run(..., resume_from=...)` raises `TypeError`.

## 3. Resume and recover `orchestral` workflows and steps

- **Live workflow unpause:** `await orch.resume(wait=True)` resumes all paused steps (`SIGCONT`, coroutines, threads, schedules) and continues remaining waves.
- **Live single-step unpause:** `await orch.resume_step(target)` by `Step`, `alias`, or run token.
- **Workflow crash/failure recovery:** rebuild the workflow with the same `workflow_id` and `checkpoint_store` (or `MERCURY_SYNC_CHECKPOINT_DB_PATH`). Then call `await orch.resume(...)` in the same or fresh process:
  ```python
  with SQLiteCheckpointStore("./state/workflow.db") as store:
      async with Orchestral(
          config=Env(MERCURY_SYNC_EXECUTOR_TYPE="none"),
          checkpoint_store=store,
          workflow_id="daily-etl",
      ) as orch:
          with orch as wf:
              s1 = wf.add_command("echo", "ready", alias="preflight")
              wf.add_task(transform_records, items, alias="transform", dependencies=[s1])

          # Skips already-completed steps (unless rerun_completed=True), restores their results,
          # and seeds remaining steps with their latest task checkpoints (last_checkpoint()).
          await orch.resume(wait=True, fail_fast=True, timeout="10m")
  ```
- **Explicit step seeding:** pass `resume_from=token | task_name | checkpoint` to `wf.add_task` or `wf.add_command`. Works with both sync and async `CheckpointStore` implementations.

## 4. Verify recovery

Check the outcome explicitly (**prove-it**, **safe-to-rerun**):

- Assert `res.status == RunStatus.COMPLETE` (`taskex`) or `orch.status == WorkflowStatus.COMPLETED` with every step `RunStatus.COMPLETE` (`orchestral`).
- Confirm checkpoint linkage (`new_run.resumed_from_checkpoint_id` in `taskex`; restored prior results and non-duplicated outputs in `orchestral`).
- Pair with `taskex`, `orchestral`, `checkpoint`, and `suspend`.

**Done when:** resumed runs finish `COMPLETE`/`COMPLETED`, checkpoint linkage is verified, and completed steps produced no duplicate side effects.

Referenced skills: `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `safe-to-rerun` (`${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md`). Read any cited skill file before acting when its trigger applies.
