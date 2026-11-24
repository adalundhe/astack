---
name: taskex
description: "Author, run, and manage tracked async/sync Python callables, shell commands, background watchers, recurring schedules, durable SQLite checkpoints, and live/crash-resumable pause-resume jobs using taskex (TaskRunner). Use for async tasks, watchers, or resumable Python automation."
disable-model-invocation: true
---

# TaskEx

Author and manage async Python coroutines, blocking callables, shell subprocesses, watchers, scheduled jobs, and checkpointed pause/resume tasks with `taskex` (`https://github.com/adalundhe/taskex`, Python >= 3.11).

## Setup and execution

- Check availability and feature support with `astack-tools doctor`; install or upgrade via `astack-tools install` (add `--from-github` if PyPI lags `main`), or `uv add taskex` inside a Python project.
- Run standalone automation scripts via `astack-tools python <script.py>` (or load the managed `uv` venv in a shell with `eval "$(astack-tools env)"`) so dependencies stay isolated from the target repo.

## Core API

```python
import asyncio
import os
from taskex import Env, RunStatus, ShellProcess, TaskRunner

async def main() -> int:
    # Executor for sync callables: "none" (async/shell or default thread pool), "thread" (blocking I/O, closures), "process" (default, picklable CPU work)
    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")
    async with TaskRunner(config=config) as runner:
        cmd_run = runner.command(
            "git", "status", "--short",
            alias="git_status",
            cwd=".",
            env={**os.environ, "GIT_PAGER": "cat"},
            timeout="10s",
        )
        res: ShellProcess = await runner.wait(cmd_run.token)
        if res.status != RunStatus.COMPLETE:
            print(f"failed ({res.return_code}): {res.error}")
            return 1
        print(res.result)
        return 0

raise SystemExit(asyncio.run(main()))
```

### Tasks, subprocesses, and schedules

- **Submit Python callables:** `run = runner.run(fn, *args, alias="name", timeout="30s", resume_from=..., **kwargs)` — runs `async def` on the loop and sync callables on the configured executor; returns a `Run` with unique Snowflake `run.token` (`"<task_name>:<run_id>"`). Use `runner.bundle(fn, *args, **kwargs)` (`functools.partial`) to bind heterogeneous calls under one alias.
- **Submit subprocesses / shell:** `run = runner.command(cmd, *args, alias="name", env=..., cwd=..., shell=False, timeout="30s", resume_from=...)`.
  - Keep `shell=False` by default (`create_subprocess_exec`). Only pass `shell=True` when pipes/globbing/builtins are needed (extra `*args` are `shlex.quote`d; never interpolate untrusted input into `cmd`).
  - **Env gotcha:** `env=...` replaces the child environment rather than merging—merge with `{**os.environ, ...}` to preserve `PATH` and tool env vars.
- **Await and inspect live output:**
  - `await runner.wait(run.token)` / `await runner.wait_all(tokens)` return typed Pydantic snapshots (`TaskRun` or `ShellProcess`), exposing `status`, `result`, `error`, `trace`, `elapsed`, `paused_duration`, and `checkpoint`.
  - `await runner.get_task_update(run.token)`, `await run.get_stdout()`, `await run.get_stderr()` read accumulated output non-destructively while running (both pipes drain concurrently so large outputs never deadlock).
- **Recurring jobs & bounded history:** pass `schedule="30s"`, `trigger="ON_START"`, `repeat="ALWAYS"` (or a positive `int`), plus retention bounds (`keep=10`, `max_age="10m"`, `keep_policy="COUNT"|"AGE"|"COUNT_AND_AGE"`). Control schedules with `await runner.pause_schedule(token)`, `await runner.resume_schedule(token)`, `await runner.cancel_schedule(token)`, or synchronous `runner.stop_schedules(task_name)`.
- **Clean lifecycle:** wrap with `async with TaskRunner(...) as runner:` (or call `await runner.shutdown()`; `await runner.stop()` cancels runs while keeping the runner alive; `runner.abort()` tears down synchronously). On POSIX, timeouts/cancellations send `SIGTERM` -> `SIGKILL` to the process group and reap children.

## Checkpointing, suspend/pause, and resume

TaskEx supports zero-signature-change `ContextVar` checkpointing, live suspend/resume, and cross-restart recovery with no extra dependencies beyond `pydantic` and stdlib `sqlite3`.

```python
import asyncio
from taskex import (
    Env, RunStatus, SQLiteCheckpointStore, TaskRunner,
    checkpoint, last_checkpoint, pause_point,
)

async def process_items(items: list[str]) -> list[str]:
    prev = last_checkpoint()
    start = prev.state["index"] if prev else 0
    out = list(prev.state["out"]) if prev else []

    for i in range(start, len(items)):
        await pause_point()  # cooperatively suspends if runner.pause(token) was called
        out.append(items[i].upper())
        await checkpoint({"index": i + 1, "out": out}, metadata={"progress": (i + 1) / len(items)})

    return out

async def main() -> int:
    with SQLiteCheckpointStore("./state/checkpoints.db", max_checkpoints_per_run=50) as store:
        async with TaskRunner(config=Env(MERCURY_SYNC_EXECUTOR_TYPE="none"), checkpoint_store=store) as runner:
            # Resume latest stored progress for "etl" if recovering from a crash, otherwise start fresh
            prev = await runner.get_latest_task_checkpoint("etl")
            run = runner.run(process_items, ["a", "b", "c"], alias="etl", resume_from=prev)
            res = await runner.wait(run.token)
            return 0 if res.status == RunStatus.COMPLETE else 1

raise SystemExit(asyncio.run(main()))
```

### Checkpointing rules and stores

- **Async vs. sync `ContextVar` helpers:**
  - Inside `async def` tasks: `last_checkpoint()`, `await pause_point()`, `await checkpoint(state, metadata=None, check_pause=True)`, `get_run_context()`. `checkpoint(...)` persists first, updates `run.latest_checkpoint`, and then honors any pending pause when `check_pause=True`.
  - Inside sync tasks on `"thread"` or `"none"` executors: `last_checkpoint()`, `pause_point_sync()`, `checkpoint_sync(state, metadata=None, check_pause=True)` (`contextvars.Context` is copied into the worker thread).
  - **`"process"` executor caveat:** `ContextVar` cannot cross OS process boundaries; use external checkpoints (`await runner.checkpoint(token, state, metadata=...)`) or switch to `"thread"` / `"none"`.
- **Stores:**
  - Default is `MemoryCheckpointStore(max_checkpoints_per_run=None)`.
  - For crash durability, use `SQLiteCheckpointStore(path, max_checkpoints_per_run=...)` (WAL mode, JSON-serializable `state` and `metadata`): either runner-managed via `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH="./state/checkpoints.db")` (closed on `shutdown()`/`abort()`), or caller-managed via `with SQLiteCheckpointStore(...) as store: TaskRunner(checkpoint_store=store)` (caller owns `store.close()`, stays open across runner restarts).
  - Custom `CheckpointStore` protocols (`save`, `get_latest`, `get_latest_for_task`, `list_checkpoints`, `delete`, `close`) may use either sync or `async def` methods—TaskEx awaits async methods automatically (and bridges them from sync thread workers).
- **External checkpoint API:** `await runner.checkpoint(token, state, metadata=...)`, `await runner.get_checkpoint(token)` (queries store even after restart), `await runner.get_latest_task_checkpoint(task_name)`, `await runner.list_checkpoints(token)`, and `await runner.clear_checkpoints(token)`.

### Suspend/pause and crash-resumable recovery

- **Live pause/resume (`RunStatus.PAUSED`):**
  - Callables: `await runner.pause(token)` suspends cooperatively at `pause_point()`/`checkpoint()` (or `pause_point_sync()`/`checkpoint_sync()` in thread workers, or before start); `await runner.resume(token)` unblocks and returns the same `Run`.
  - Shell commands (POSIX): `await runner.pause(token)` sends `SIGSTOP` to the subprocess process group (or defers spawn); `await runner.resume(token)` sends `SIGCONT`.
  - Recurring schedules: `await runner.pause_schedule(token)` suspends future iterations and pauses the active run; `await runner.resume_schedule(token)` resumes both.
  - **Pause-aware timeouts & cleanup safety:** `timeout` countdowns freeze while `PAUSED` (tracked in `res.paused_duration`). Cancelling a `PAUSED` run unblocks blocked sync threads (`CancelledError`) and sends `SIGCONT`+`SIGTERM` to `SIGSTOP`-paused subprocesses so nothing hangs. Retention sweeps (`COUNT`/`AGE`) never evict live or `PAUSED` runs and never delete persisted checkpoints.
- **Restart-from-checkpoint recovery:**
  - Calling `await runner.resume(old_token_or_task_name, *args, call=fn, **kwargs)` on a failed, cancelled, or completed run—or on a fresh `TaskRunner` sharing the same `SQLiteCheckpointStore`—loads the latest stored checkpoint and starts a new `Run` (`run.resumed_from_checkpoint_id`) seeded so `last_checkpoint()` returns it immediately.
  - Or pass `resume_from=old_token | task_name | checkpoint` directly to `runner.run(...)` / `runner.command(...)` (sync stores only; with an async `CheckpointStore`, use `await runner.resume(...)` or pass a pre-loaded `Checkpoint`).

## Result checking & script hygiene

- Exit code `0` sets `res.status == RunStatus.COMPLETE` (`res.result` = `stdout`, `res.error` = `stderr` if non-empty); non-zero, timeout, or spawn failure sets `RunStatus.FAILED` (check `res.return_code`, `res.error`, `res.trace`).
- Always check `res.status` explicitly and exit non-zero on failure (**no-hidden-flow-control**).
- Save reusable repo automation in `scripts/` and make reruns safe with checkpoints or state convergence (**safe-to-rerun**). Use **checkpoint**, **suspend**, and **resume** for step-by-step checkpointing, pause, and crash-recovery playbooks; use **orchestral** for dependency-graph (DAG) waves with cycle checks, branch-aware skipping, and workflow-level pause/resume recovery, or **werkflow** for decorator DAGs with inter-step data injection and `werkflow-modules` integrations.

Referenced skills: `no-hidden-flow-control` (`${CLAUDE_SKILL_DIR}/../no-hidden-flow-control/SKILL.md`), `safe-to-rerun` (`${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md`), `checkpoint` (`${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`), `suspend` (`${CLAUDE_SKILL_DIR}/../suspend/SKILL.md`), `resume` (`${CLAUDE_SKILL_DIR}/../resume/SKILL.md`), `orchestral` (`${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`), `werkflow` (`${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`). Read any cited skill file before acting when its trigger applies.
