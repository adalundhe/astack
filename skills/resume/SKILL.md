---
name: resume
description: "Resume suspended (PAUSED) taskex runs/schedules and orchestral workflows/steps in place, or recover failed, cancelled, or crashed taskex and orchestral runs from durable SQLite checkpoints without duplicating completed work. Use when unpausing or restarting interrupted automation."
disable-model-invocation: true
---

# Resume

Unpause live `PAUSED` runs, schedules, steps, or workflows in place—or recover failed, cancelled, and crashed `taskex` / `orchestral` runs from durable checkpoints.

## 1. Choose live unpause vs. checkpoint recovery

- **Live unpause (same runner, `PAUSED`):** continues the exact run or workflow in place and unfreezes pause-aware timeouts.
- **Restart-from-checkpoint (failed, cancelled, or fresh process with `SQLiteCheckpointStore`):** loads saved checkpoints so completed steps skip and incomplete steps start with `last_checkpoint()` populated.

## 2. Resume `taskex` runs and schedules

- **Live unpause:**
  - Single run (async/thread callable or `SIGSTOP`-paused POSIX shell command): `run = await runner.resume(token)` (returns the same `Run`; sends `SIGCONT` to paused POSIX process groups).
  - Recurring schedule: `await runner.resume_schedule(token)` (unpauses active run and schedule loop).
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
  - **Async store gotcha (`taskex`):** with an async `CheckpointStore`, use `await runner.resume(...)` or pass an already-awaited `Checkpoint` object to `resume_from=`; passing a string token to sync `runner.run(..., resume_from=...)` raises `TypeError`.

## 3. Resume and recover `orchestral` workflows and steps

- **Live workflow unpause:** `await orch.resume(wait=True)` resumes all paused steps (`SIGCONT` / unblocks coroutines & threads / schedules) and continues remaining waves.
- **Live single-step unpause:** `await orch.resume_step(target)` (by `Step`, name/`alias`, or run token).
- **Workflow crash/failure recovery (same instance or fresh process):** rebuild the workflow with the same `workflow_id` and `checkpoint_store` (or `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH=...)`) and call `await orch.resume(...)`:
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
- **Explicit step-level seeding:** seed individual steps with `wf.add_task(..., resume_from=token | task_name | checkpoint)` or `wf.add_command(..., resume_from=...)` (works with both sync and async `CheckpointStore` implementations).

## 4. Verify recovery

Check the outcome explicitly (**prove-it**, **no-hidden-flow-control**, **safe-to-rerun**):
- Assert `res.status == RunStatus.COMPLETE` (for `taskex`) or `orch.status == WorkflowStatus.COMPLETED` with every step `RunStatus.COMPLETE` (for `orchestral`).
- Confirm checkpoint linkage (`new_run.resumed_from_checkpoint_id` in `taskex`; restored prior step results and non-duplicated outputs in `orchestral`).
- Pair with **taskex**, **orchestral**, **checkpoint**, and **suspend**.
