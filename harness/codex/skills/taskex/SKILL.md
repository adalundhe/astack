---
name: taskex
description: "Author, run, and manage tracked async Python callables, blocking functions, shell commands, background watchers, and recurring jobs using taskex (TaskRunner). Use when writing lightweight async task or watcher scripts."
---

# TaskEx

Author and manage asynchronous Python functions, blocking callables, shell subprocesses, background watchers, and scheduled jobs with `taskex` (`https://github.com/adalundhe/taskex`, Python >= 3.11).

## Setup and execution

- Check availability with `astack-tools doctor`; install via `astack-tools install` (or `uv add taskex` inside a Python project).
- Run standalone automation scripts via `astack-tools python <script.py>` so dependencies stay isolated from the target repo.

## Core API

```python
import asyncio
import os
from taskex import Env, RunStatus, ShellProcess, TaskRun, TaskRunner

async def main() -> int:
    # Choose executor: "none" (async/shell-only), "thread" (blocking I/O, closures), "process" (default, CPU-bound picklable)
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

### Key methods and patterns

- **Submit Python callables:** `run = runner.run(fn, *args, alias="name", timeout="30s", **kwargs)` — works for both `async def` and sync functions; returns a `Run` with unique `run.token` (`"<task_name>:<run_id>"`).
- **Submit subprocesses / shell:** `run = runner.command(cmd, *args, alias="name", env=..., cwd=..., shell=False, timeout="30s")`.
  - Keep `shell=False` by default (uses `create_subprocess_exec`). Only pass `shell=True` when pipes/globbing/builtins are needed, and never interpolate untrusted input.
  - **Env gotcha:** passing `env=...` replaces the child environment rather than merging—merge with `{**os.environ, ...}` to preserve `PATH` and tool env vars.
- **Await and inspect live output:**
  - `await runner.wait(run.token)` / `await runner.wait_all(tokens)` return typed Pydantic snapshots (`TaskRun` or `ShellProcess`).
  - `await runner.get_task_update(run.token)`, `await run.get_stdout()`, `await run.get_stderr()` read accumulated output non-destructively while the process is running (stdout/stderr are drained concurrently so large outputs never deadlock OS pipes).
- **Recurring jobs & bounded history:** pass `schedule="30s"`, `trigger="ON_START"`, `repeat="ALWAYS"` (or an integer), plus retention bounds (`keep=10`, `max_age="10m"`, `keep_policy="COUNT"|"AGE"|"COUNT_AND_AGE"`). Stop with `await runner.cancel_schedule(run.token)` or `runner.stop_schedules(task_name)`.
- **Clean lifecycle:** always wrap with `async with TaskRunner(...) as runner:` (or call `await runner.shutdown()`; `await runner.stop()` cancels runs while keeping the runner alive; `runner.abort()` tears down synchronously). On POSIX, timeouts/cancellations send `SIGTERM` -> `SIGKILL` to the whole process group and reap children.

## Result checking & script hygiene

- Exit code `0` sets `res.status == RunStatus.COMPLETE` (`res.result` = `stdout`, `res.error` = `stderr` if non-empty); non-zero, timeout, or spawn failure sets `RunStatus.FAILED` (check `res.return_code`, `res.error`, `res.trace`).
- Always check `res.status` explicitly and exit non-zero on failure (**no-hidden-flow-control**).
- Save reusable repo automation in `scripts/` and make reruns safe (**safe-to-rerun**). Use **orchestral** instead when you need ordered multi-stage concurrent groups, or **werkflow** for named DAGs and external integrations.

Referenced skills: `no-hidden-flow-control` (`../no-hidden-flow-control/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`), `orchestral` (`../orchestral/SKILL.md`), `werkflow` (`../werkflow/SKILL.md`). Read any cited skill file before acting when its trigger applies.
