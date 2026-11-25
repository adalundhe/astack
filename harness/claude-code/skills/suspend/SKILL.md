---
name: suspend
description: "Cleanly suspend (pause) running taskex callables, POSIX shell process groups, recurring schedules, or orchestral workflows and individual DAG steps without losing progress or tripping timeouts."
disable-model-invocation: true
---

# Suspend

Pause active `taskex` tasks, subprocesses, schedules, or `orchestral` workflows cleanly without losing progress or leaking zombie processes.

## 1. Identify the active runner

Check whether the workload uses `taskex` (`TaskRunner`) or `orchestral` (`Orchestral`), and verify capabilities via `astack-tools doctor` (`taskex_checkpoints`, `orchestral_checkpoints`).

## 2. Suspend a live `taskex` run or schedule

- **Async callables:** `await runner.pause(run.token)` marks `RunStatus.PAUSED` and suspends at the next `pause_point()` or `checkpoint(..., check_pause=True)`.
- **Thread-pool sync callables (`"thread"` / `"none"`):** `await runner.pause(run.token)` blocks the worker thread at `pause_point_sync()` or `checkpoint_sync()`. For `"process"` tasks, save an external **checkpoint** at a safe boundary before stopping.
- **Shell commands (POSIX):** `await runner.pause(run.token)` sends `SIGSTOP` to the subprocess process group (or defers spawn).
- **Recurring schedules:** `await runner.pause_schedule(run.token)` halts future ticks and pauses the active run without deleting the schedule.

## 3. Suspend a live `orchestral` workflow or step

- **Whole workflow:** `await orch.pause()` (when started with `wait=False`) sets `WorkflowStatus.PAUSED`, freezes workflow and step timeouts, pauses active tasks and POSIX subprocesses (`SIGSTOP`), blocks later waves, and saves a durable checkpoint for `orch.workflow_id`.
- **Single step (siblings keep running):** `await orch.pause_step(target)` accepts a `Step`, `alias`, or run token from `orch.active_tokens`.

## 4. Safety guarantees while suspended

- **Pause-aware timeouts:** timeout countdowns freeze while `PAUSED` (`paused_duration`), so long pauses never trigger false timeouts.
- **Retention safety:** `COUNT` and `AGE` sweeps never evict live or `PAUSED` runs and never delete checkpoints.
- **Safe cancellation:** `cancel`, `stop`, `shutdown`, and `abort` unblock paused threads and send `SIGCONT` + `SIGTERM` to `SIGSTOP`-paused subprocesses so nothing hangs.

## 5. Verify and hand off state

- **`taskex`:** confirm `runner.get_run_status(token) == RunStatus.PAUSED`, inspect `get_task_update(token)`, and record `token` plus the SQLite DB path for **resume**.
- **`orchestral`:** confirm `orch.status == WorkflowStatus.PAUSED` (or step status), and record `orch.workflow_id` plus the SQLite DB path for **resume**. See **taskex** and **orchestral** for full runner APIs.

Referenced skills: `checkpoint` (`${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`), `resume` (`${CLAUDE_SKILL_DIR}/../resume/SKILL.md`), `taskex` (`${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`), `orchestral` (`${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`). Read any cited skill file before acting when its trigger applies.
