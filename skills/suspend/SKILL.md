---
name: suspend
description: "Cleanly suspend (pause) running taskex callables, POSIX shell process groups, recurring schedules, or orchestral workflows and individual DAG steps without losing progress or tripping timeouts. Use when pausing active automation for maintenance, backpressure, or human review."
disable-model-invocation: true
---

# Suspend

Pause active `taskex` tasks, subprocesses, schedules, or `orchestral` workflows (whole workflow or individual steps) cleanly without losing progress or leaving zombie processes behind.

## 1. Identify the active runner

Check whether the workload is managed by `taskex` (`TaskRunner`) or `orchestral` (`Orchestral`), and verify capabilities with `astack-tools doctor` (`taskex_checkpoints` and `orchestral_checkpoints`).

## 2. Suspend a live `taskex` run or schedule

- **Async callables:** `await runner.pause(run.token)` -> marks `RunStatus.PAUSED`; suspends cooperatively at the next `await pause_point()` or `await checkpoint(..., check_pause=True)` (or before start if paused immediately).
- **Thread-pool sync callables (`"thread"` / `"none"`):** `await runner.pause(run.token)` -> blocks the worker thread at `pause_point_sync()` or `checkpoint_sync()`. (For `"process"` tasks without cooperative points, wait for a safe boundary or save an external **checkpoint** before stopping.)
- **Shell commands (POSIX):** `await runner.pause(run.token)` -> sends `SIGSTOP` to the subprocess process group (`start_new_session=True`), or defers spawn if not started yet.
- **Recurring schedules:** `await runner.pause_schedule(run.token)` -> halts future iterations **and** pauses the active run without removing the schedule.

## 3. Suspend a live `orchestral` workflow or step

- **Whole workflow:** `await orch.pause()` (typically started with `await orch.run(wait=False, ...)`):
  - Transitions status to `WorkflowStatus.PAUSED` (`orch.is_paused == True`).
  - Freezes both workflow-level and step-level timeouts (`orch.paused_duration`).
  - Pauses all active async/thread callables, POSIX shell subprocesses (`SIGSTOP`), and repeating schedules.
  - Prevents subsequent waves from launching and saves a durable workflow checkpoint for `orch.workflow_id`.
- **Single step (siblings keep running):** `await orch.pause_step(target)` where `target` is a `Step` object, step name/`alias`, or run token (inspect `orch.active_tokens`).

## 4. Safety guarantees while suspended

- **Pause-aware timeouts:** configured step and workflow `timeout` countdowns freeze while `PAUSED`, so pausing longer than the timeout never causes a false failure (`res.paused_duration`, `orch.paused_duration`).
- **Retention safety:** background `COUNT` / `AGE` cleanup sweeps never evict live or `PAUSED` runs and never delete persisted checkpoints.
- **Safe cancellation while paused:** calling `await runner.cancel(token)` or `await orch.stop()` / `await orch.shutdown()` / `orch.abort()` while paused unblocks waiting sync threads (`CancelledError`) and sends `SIGCONT` + `SIGTERM` to `SIGSTOP`-paused POSIX process groups so nothing hangs or zombies.

## 5. Verify suspension and hand off state

Before stepping away:
- For `taskex`: assert `runner.get_run_status(token) == RunStatus.PAUSED`, inspect `await runner.get_task_update(token)` (including `.checkpoint`), and record `token` and the SQLite DB path for **resume**.
- For `orchestral`: assert `orch.status == WorkflowStatus.PAUSED` (or step status when using `pause_step`), confirm `orch.workflow_id` and checkpoint DB path are recorded for **resume**. See **taskex** and **orchestral** for full runner details.
