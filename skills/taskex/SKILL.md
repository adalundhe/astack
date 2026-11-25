---
name: taskex
description: "Author, run, and manage tracked async/sync Python callables, shell commands, watchers, recurring schedules, SQLite checkpoints, and live/crash-resumable pause-resume jobs using taskex (TaskRunner). Use for async tasks, watchers, or resumable Python automation."
disable-model-invocation: true
---

# TaskEx

Run and supervise async coroutines, sync callables, shell commands, watchers, recurring schedules, and checkpointed pause/resume tasks with `taskex` (`https://github.com/adalundhe/taskex`, Python >= 3.11).

## Setup and execution

- Check availability with `astack-tools doctor`; install or upgrade via `astack-tools install` (`--from-github` if PyPI lags `main`), or `uv add taskex` inside a Python project.
- Run standalone scripts via `astack-tools python <script.py>` (or `eval "$(astack-tools env)"`) so deps stay isolated from the repo.

## Core API

```python
import asyncio
import os
from taskex import Env, RunStatus, ShellProcess, TaskRunner

async def main() -> int:
    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")  # "none" | "thread" | "process"
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

- **Python callables:** `runner.run(fn, *args, alias="name", timeout="30s", resume_from=..., **kwargs)` runs async functions on the loop and sync functions on the configured executor, returning a `Run` with unique `run.token`. Use `runner.bundle(fn, *args, **kwargs)` to bind varied calls under one alias.
- **Shell commands:** `runner.command(cmd, *args, alias="name", env=..., cwd=..., shell=False, timeout="30s", resume_from=...)`. Keep `shell=False` by default, and never interpolate untrusted input into `cmd`.
- **Env gotcha:** `env=...` replaces the child environment instead of merging. Pass `{**os.environ, ...}` to preserve `PATH`.
- **Inspecting results:** `await runner.wait(token)` and `wait_all(tokens)` return typed snapshots (`status`, `result`, `error`, `trace`, `elapsed`, `paused_duration`, `checkpoint`). Read live output via `get_task_update(token)`, `run.get_stdout()`, and `run.get_stderr()`.
- **Schedules & retention:** pass `schedule="30s"`, `trigger="ON_START"`, `repeat="ALWAYS"` (or `int`), plus `keep`, `max_age`, and `keep_policy`. Control schedules with `pause_schedule`, `resume_schedule`, `cancel_schedule`, or `stop_schedules`.
- **Clean lifecycle:** use `async with TaskRunner(...) as runner:` (or `shutdown()` / `stop()` / `abort()`). On POSIX, timeouts send `SIGTERM` -> `SIGKILL` to the process group and reap children.

## Checkpointing, pause, and crash recovery

`taskex` supports `ContextVar` checkpointing, live suspend/resume, and restart recovery using stdlib `sqlite3`.

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
        await pause_point()
        out.append(items[i].upper())
        await checkpoint({"index": i + 1, "out": out}, metadata={"progress": (i + 1) / len(items)})

    return out

async def main() -> int:
    with SQLiteCheckpointStore("./state/checkpoints.db", max_checkpoints_per_run=50) as store:
        async with TaskRunner(config=Env(MERCURY_SYNC_EXECUTOR_TYPE="none"), checkpoint_store=store) as runner:
            prev = await runner.get_latest_task_checkpoint("etl")
            run = runner.run(process_items, ["a", "b", "c"], alias="etl", resume_from=prev)
            res = await runner.wait(run.token)
            return 0 if res.status == RunStatus.COMPLETE else 1

raise SystemExit(asyncio.run(main()))
```

### Rules and stores

- **Async helpers:** `last_checkpoint()`, `await pause_point()`, `await checkpoint(state, metadata=None, check_pause=True)`, `get_run_context()`. `checkpoint()` persists first, then honors any pending pause.
- **Sync helpers (`"thread"` / `"none"`):** `last_checkpoint()`, `pause_point_sync()`, `checkpoint_sync(...)`.
- **`"process"` caveat:** `ContextVar` cannot cross OS processes; use external `await runner.checkpoint(token, state)` or switch to `"thread"` / `"none"`.
- **Stores:** default is `MemoryCheckpointStore`. For crash durability, use `SQLiteCheckpointStore(path)` (WAL mode, JSON-serializable state) via `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH=...)` (runner-managed) or `with SQLiteCheckpointStore(...) as store:` (caller-managed across restarts). Custom `CheckpointStore` implementations may use sync or async methods.
- **External checkpoint API:** `runner.checkpoint`, `get_checkpoint`, `get_latest_task_checkpoint`, `list_checkpoints`, and `clear_checkpoints`.

### Pause/resume and restart recovery

- **Live pause (`RunStatus.PAUSED`):** `await runner.pause(token)` suspends callables at `pause_point()`/`checkpoint()` or sends `SIGSTOP` to POSIX shell process groups. `await runner.resume(token)` unblocks them (`SIGCONT`). Timeouts freeze while paused, and cancelling a paused run safely unblocks threads and sends `SIGCONT`+`SIGTERM`.
- **Restart recovery:** call `await runner.resume(old_token_or_task_name, *args, call=fn, **kwargs)` (even in a fresh `TaskRunner` sharing the SQLite store), or pass `resume_from=...` to `runner.run(...)` / `runner.command(...)`.

## Hygiene

- Check `res.status` explicitly and exit non-zero on failure (**no-hidden-flow-control**).
- Save reusable repo scripts in `scripts/` and make reruns idempotent (**safe-to-rerun**).
- See **checkpoint**, **suspend**, and **resume** for operational playbooks; use **orchestral** for DAG waves or **werkflow** for `@step` data injection and `werkflow-modules`.
