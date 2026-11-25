---
name: suspend
description: "Pause running taskex tasks, POSIX shell process groups, schedules, or orchestral DAG workflows cleanly. Use when pausing Python automation runs."
---

# Suspend

Pause active `taskex` tasks, subprocesses, schedules, or `orchestral` workflows cleanly without losing progress or leaking processes.

**Scope:** use this skill only for Python `taskex` or `orchestral` runs. For agentic `lead` programs, wind down lanes cleanly and resume later via `whatsup`. Note that Windows lacks POSIX `SIGSTOP`, so shell-command suspension applies on POSIX only.

## 1. Identify the active runner

Check whether the workload uses `taskex` (`TaskRunner`) or `orchestral` (`Orchestral`). Confirm capabilities with `astack-tools doctor` (`taskex_checkpoints`, `orchestral_checkpoints`).

## 2. Suspend a live `taskex` run or schedule

- **Async callables:** call `await runner.pause(run.token)`. It marks `RunStatus.PAUSED` and suspends at the next `pause_point()` or `checkpoint(..., check_pause=True)`.
- **Thread-pool sync callables (`"thread"` / `"none"`):** `await runner.pause(run.token)` blocks the worker at `pause_point_sync()` or `checkpoint_sync()`. For `"process"` tasks, save an external **checkpoint** at a safe boundary before stopping.
- **Shell commands (POSIX only):** `await runner.pause(run.token)` sends `SIGSTOP` to the subprocess process group, or defers spawn.
- **Recurring schedules:** `await runner.pause_schedule(run.token)` halts future ticks and pauses the active run without deleting the schedule.

## 3. Suspend a live `orchestral` workflow or step

- **Whole workflow:** start the workflow with `wait=False` so your caller keeps control while waves run. Then call `await orch.pause()`. It sets `WorkflowStatus.PAUSED`, freezes timeouts, pauses active tasks and POSIX subprocesses (`SIGSTOP`), blocks later waves, and saves a durable checkpoint for `orch.workflow_id`.
- **Single step:** call `await orch.pause_step(target)` with a `Step`, `alias`, or token from `orch.active_tokens`. Sibling steps keep running.

## 4. Safety guarantees while suspended

- **Pause-aware timeouts:** timeout clocks freeze while `PAUSED` (`paused_duration`), so long pauses never trigger false timeouts.
- **Retention safety:** `COUNT` and `AGE` sweeps never evict live or `PAUSED` runs and never delete checkpoints.
- **Safe cancellation:** `cancel`, `stop`, `shutdown`, and `abort` unblock paused threads and send `SIGCONT` + `SIGTERM` to `SIGSTOP`-paused subprocesses so nothing hangs.

## 5. Verify and hand off state

- **`taskex`:** confirm `runner.get_run_status(token) == RunStatus.PAUSED` and check `get_task_update(token)`. Record `token` and the SQLite DB path for **resume**.
- **`orchestral`:** confirm `orch.status == WorkflowStatus.PAUSED` (or step status). Record `orch.workflow_id` and the SQLite DB path for **resume**.

**Reply:** state the paused `token` or `workflow_id`, confirmed `PAUSED` status, checkpoint DB path, and exact **resume** handoff.

Referenced skills: `checkpoint` (`../checkpoint/SKILL.md`), `resume` (`../resume/SKILL.md`). Read any cited skill file before acting when its trigger applies.
