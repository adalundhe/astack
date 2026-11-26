---
name: taskex
description: "Turn prompts into saved TaskEx scripts, watchers, and schedules, or run, pause, resume, and manage them. Use for general Python automation and background tasks."
---

# TaskEx

Turn a prompt into a saved TaskEx script, watcher, or schedule—or inspect, run, pause, resume, update, and manage existing ones with `taskex` (`https://github.com/adalundhe/taskex`, Python >= 3.11).

**When to choose TaskEx:** reach for TaskEx almost anywhere you need general automation. It handles tracked async/sync tasks, background task management, safe subprocesses, watchers, recurring schedules, keep/discard retention policies, and resumable jobs. TaskEx works cleanly both standalone and alongside `werkflow` or any `werkflow-modules` package.

## Storage, setup, and lifecycle (cross-OS)

- **Canonical path:** `$HOME/.astack/<project_name>/automations/<automation_name>/` (`%USERPROFILE%\.astack\<project_name>\automations\<automation_name>\` on Windows; `ASTACK_HOME` overrides). Keep scripts in repo `scripts/` only when the user wants them checked into git.
- Resolve and create folders via `astack-tools automations path <project_name> <automation_name> --ensure`. List saved scripts via `astack-tools automations list [--project <project_name>] --runner taskex [--json]`.
- Check `automation.mode` in `~/.config/astack/settings.json` and run `astack-tools doctor --json` (`taskex_checkpoints`). Under `agentic-only`, ask permission before installing Python packages or running **setup**.
- Under `python-stack`, install via `astack-tools install` (`--modules <list>` for optional `werkflow-modules`, `--from-github` if PyPI lags `main`). Inside a Python repo, you can also run `uv add taskex`. Run standalone scripts via `astack-tools python "<automation_dir>/task.py"` (or `eval "$(astack-tools env)"`).
- **Manage by intent:**
  1. **List / inspect:** run `astack-tools automations list --project <project_name> --runner taskex`. Read `automation.json`, the entrypoint, and `state/` checkpoint status.
  2. **Create from a prompt:** check **rtfm**, **lookup**, and **analyze-environment** first. Clarify only missing inputs, cadence, timeouts, retention, or credentials. Keep logic deterministic in Python and safe subprocess calls.
  3. **Run:** honor `autonomy` (**decisions-in-plain-words**). Test a single `--once` or dry-run pass against a safe target before mutating live systems.
  4. **Pause, resume, update, or retire:** manage live tasks and schedules with **checkpoint**, **suspend**, and **resume** (`pause_schedule`, `resume_schedule`, `cancel_schedule`). When editing checkpointed tasks, check compatibility with `state/checkpoints.db` (or support `--clear-checkpoints`). Confirm before deleting a saved script.

## Folder layout

Keep each `<automation_name>/` folder self-contained:

- `automation.json`: metadata (`runner`: `"taskex"`, `entrypoint`: `"task.py"`, `description`, optional `modules` if using `werkflow-modules`, `updated` UTC).
- `task.py`: exposes clear CLI flags (`--dry-run`, `--once`, `--resume`, `--clear-checkpoints`) and stores checkpoints at `Path(__file__).resolve().parent / "state" / "checkpoints.db"` when durability matters.
- `config.example.json` (if parameterized) without secrets; read credentials from env vars or secret managers (**no-leaked-secrets**).
- `state/`: SQLite checkpoint database (keep payloads compact and secret-free).

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

### Tasks, subprocesses, `werkflow-modules`, and schedules

- **Python callables.** Call `runner.run(fn, *args, alias="name", timeout="30s", resume_from=..., **kwargs)` to get a `Run` with `run.token`. Use `runner.bundle(fn, *args, **kwargs)` (a `functools.partial` helper) to pre-bind arguments before passing a callable to `runner.run(...)` or schedules.
- **Using `werkflow-modules`.** Import any `werkflow-*` module (`Shell`, `Git`, `Github`, `HTTP`, `Docker`, `AWS`, `Jira`, `Secrets`, etc.; see **werkflow**) directly inside async TaskEx callables. Install needed extras via `astack-tools install --modules <list>`, and close each module in a `finally:` block.
- **Shell commands.** Call `runner.command(cmd, *args, alias="name", env=..., cwd=..., shell=False, timeout="30s", resume_from=...)`. Keep `shell=False` and pass separate arg strings, because shell expansion opens command injection.
- **Env gotcha.** `env=...` replaces the child environment instead of merging. Pass `{**os.environ, ...}` to preserve `PATH`.
- **Inspecting results.** `await runner.wait(token)` and `wait_all(tokens)` return typed snapshots (`status`, `result`, `error`, `trace`, `elapsed`, `paused_duration`, `checkpoint`). Read live streams via `get_task_update(token)`, `run.get_stdout()`, and `run.get_stderr()`.
- **Schedules & keep/discard retention.** Pass `schedule="30s"`, `trigger="ON_START"`, `repeat="ALWAYS"` (or `int`), plus `keep`, `max_age`, and `keep_policy`. Control schedules via `pause_schedule`, `resume_schedule`, `cancel_schedule`, or `stop_schedules`.
- **Clean lifecycle.** Use `async with TaskRunner(...) as runner:` (or `shutdown()` / `stop()` / `abort()`), handling `SIGINT`/`SIGTERM` cleanly so no orphan subprocesses remain. On POSIX, timeouts send `SIGTERM` then `SIGKILL` to the process group.

## Checkpointing, pause, and crash recovery

`taskex` supports `ContextVar` checkpointing, live suspend/resume, and restart recovery using stdlib `sqlite3`.

```python
import asyncio
from pathlib import Path
from taskex import (
    Env, RunStatus, SQLiteCheckpointStore, TaskRunner,
    checkpoint, last_checkpoint, pause_point,
)

STATE_DB = Path(__file__).resolve().parent / "state" / "checkpoints.db"

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
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    with SQLiteCheckpointStore(str(STATE_DB), max_checkpoints_per_run=50) as store:
        async with TaskRunner(config=Env(MERCURY_SYNC_EXECUTOR_TYPE="none"), checkpoint_store=store) as runner:
            prev = await runner.get_latest_task_checkpoint("etl")
            run = runner.run(process_items, ["a", "b", "c"], alias="etl", resume_from=prev)
            res = await runner.wait(run.token)
            return 0 if res.status == RunStatus.COMPLETE else 1

raise SystemExit(asyncio.run(main()))
```

### Playbooks and store pointers

- **Checkpoints (`checkpoint`).** Use `last_checkpoint()`, `await checkpoint(...)`, or `checkpoint_sync(...)` (`"thread"` / `"none"`). For `"process"` tasks, call `await runner.checkpoint(token, state)` because `ContextVar` cannot cross OS processes. Default store is `MemoryCheckpointStore`; pass `SQLiteCheckpointStore(path)` or `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH=...)` for crash durability.
- **Live pause (`suspend`).** Call `await runner.pause(token)` to pause at `pause_point()`/`checkpoint()`, or send `SIGSTOP` to POSIX shell groups. Timeouts freeze while paused.
- **Recovery (`resume`).** Call `await runner.resume(token_or_name, *args, call=fn, **kwargs)` on a live or fresh `TaskRunner` sharing the SQLite store. You can also pass `resume_from=...` to `runner.run(...)` or `runner.command(...)`.

## Verify and compare

- Run a bounded `--once` or dry-run pass via `astack-tools python`. Check `res.status` explicitly and exit non-zero on failure (**prove-it**, **no-hidden-flow-control**, **safe-to-rerun**).
- Prefer **orchestral** for shorter, scriptish shell or stdlib-Python DAG waves. Prefer **werkflow** for composed `werkflow-modules`, implicit state-passing, and multi-workflow pipelines.

**Done when:** the script is saved under `$HOME/.astack/<project_name>/automations/<automation_name>/` (or Windows equivalent) and runs via `astack-tools python`. It checks `res.status`, exits non-zero on failure, survives an idempotent rerun or resume, and your reply gives exact run and resume commands.

Referenced skills: `setup` (`../astack-setup/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `lookup` (`../lookup/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`), `checkpoint` (`../checkpoint/SKILL.md`), `suspend` (`../suspend/SKILL.md`), `resume` (`../resume/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `werkflow` (`../werkflow/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `no-hidden-flow-control` (`../no-hidden-flow-control/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`), `orchestral` (`../orchestral/SKILL.md`). Read any cited skill file before acting when its trigger applies.
