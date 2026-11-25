---
name: taskex
description: "Run tracked async/sync Python callables, shell commands, schedules, and resumable jobs with taskex. Use for async tasks, watchers, or resumable Python automation."
disable-model-invocation: true
---

# TaskEx

Run and supervise async coroutines, sync callables, shell commands, watchers, schedules, and resumable jobs with `taskex` (`https://github.com/adalundhe/taskex`, Python >= 3.11).

## Setup and execution

- Check `automation.mode` in `~/.config/astack/settings.json` and run `astack-tools doctor`. Never install Python packages under `agentic-only` without permission.
- Under `python-stack`, install via `astack-tools install` (`--from-github` if PyPI lags `main`), or `uv add taskex` inside a Python repo.
- Run standalone scripts via `astack-tools python <script.py>` (or `eval "$(astack-tools env)"`). Dependencies then stay isolated from the repo.

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

- **Python callables.** Call `runner.run(fn, *args, alias="name", timeout="30s", resume_from=..., **kwargs)` to get a `Run` with `run.token`. Use `runner.bundle(fn, *args, **kwargs)` (a `functools.partial` helper) to pre-bind arguments before passing a callable to `runner.run(...)` or schedules.
- **Shell commands.** Call `runner.command(cmd, *args, alias="name", env=..., cwd=..., shell=False, timeout="30s", resume_from=...)`. Keep `shell=False` and pass separate arg strings, because shell expansion opens command injection.
- **Env gotcha.** `env=...` replaces the child environment instead of merging. Pass `{**os.environ, ...}` to preserve `PATH`.
- **Inspecting results.** `await runner.wait(token)` and `wait_all(tokens)` return typed snapshots (`status`, `result`, `error`, `trace`, `elapsed`, `paused_duration`, `checkpoint`). Read live streams via `get_task_update(token)`, `run.get_stdout()`, and `run.get_stderr()`.
- **Schedules & retention.** Pass `schedule="30s"`, `trigger="ON_START"`, `repeat="ALWAYS"` (or `int`), plus `keep`, `max_age`, and `keep_policy`. Control schedules via `pause_schedule`, `resume_schedule`, `cancel_schedule`, or `stop_schedules`.
- **Clean lifecycle.** Use `async with TaskRunner(...) as runner:` (or `shutdown()` / `stop()` / `abort()`). On POSIX, timeouts send `SIGTERM` then `SIGKILL` to the process group.

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

### Playbooks and store pointers

- **Checkpoints (`checkpoint`).** Use `last_checkpoint()`, `await checkpoint(...)`, or `checkpoint_sync(...)` (`"thread"` / `"none"`). For `"process"` tasks, call `await runner.checkpoint(token, state)` because `ContextVar` cannot cross OS processes. Default store is `MemoryCheckpointStore`. For crash durability, pass `SQLiteCheckpointStore(path)` or set `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH=...)`.
- **Live pause (`suspend`).** Call `await runner.pause(token)` to pause at `pause_point()`/`checkpoint()`, or send `SIGSTOP` to POSIX shell groups. Timeouts freeze while paused.
- **Recovery (`resume`).** Call `await runner.resume(token_or_name, *args, call=fn, **kwargs)` on a live or fresh `TaskRunner` sharing the SQLite store. Or pass `resume_from=...` to `runner.run(...)` or `runner.command(...)`.

## Hygiene

- Check `res.status` explicitly and exit non-zero on failure (**no-hidden-flow-control**).
- Save reusable repo scripts in `scripts/` and make reruns idempotent (**safe-to-rerun**).
- Prefer `orchestral` for DAG waves, or `werkflow` for `@step` data injection and `werkflow-modules`.

**Done when:** the script runs via `astack-tools python`, checks `res.status`, exits non-zero on failure, and survives an idempotent rerun or resume.

Referenced skills: `no-hidden-flow-control` (`../no-hidden-flow-control/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`). Read any cited skill file before acting when its trigger applies.
