---
name: orchestral
description: "Author, run, and manage multi-stage concurrent Python and shell pipelines using orchestral (Orchestral, Group, fail_fast, streaming batches). Use for structured parallel build/test/benchmark scripts and staged automation."
---

# Orchestral

Author and manage multi-stage concurrent pipelines mixing shell commands, `async def` coroutines, and sync Python functions with `orchestral` (`https://github.com/adalundhe/orchestral`, built on `taskex`, Python >= 3.11).

## Setup and execution

- Check availability with `astack-tools doctor`; install via `astack-tools install` (or `uv add orchestral`).
- Run scripts via `astack-tools python <script.py>`.

## Execution model & core API

**Groups run strictly in order; all steps inside a group run concurrently.**

```python
import asyncio
from taskex import Env, RunStatus
from orchestral import Orchestral, WorkflowStatus

async def fetch_metrics(target: str) -> dict:
    ...

async def main() -> int:
    # Use "none" for pure shell/async, "thread" for blocking I/O or closures, "process" (default) for picklable CPU work
    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="thread")

    async with Orchestral(config=config) as orch:
        with orch as workflow:
            # Stage 1: concurrent preparation / checks
            prep = workflow.group()
            prep.add_command("ruff", "check", ".", alias="lint", timeout="60s")
            prep.add_command("pytest", "-q", "tests/unit", alias="unit", timeout="2m")

            # Stage 2: runs only after Stage 1 completes
            bench = workflow.group()
            bench.add_task(fetch_metrics, "main", alias="metrics", timeout="5m")

        await orch.run(wait=True, fail_fast=True, timeout="10m")

        if orch.status != WorkflowStatus.COMPLETED:
            print(f"workflow {orch.status.value}: {orch.error}")
            return 1
        for name, runs in orch.results.items():
            for run_id, res in runs.items():
                if res.status != RunStatus.COMPLETE:
                    print(f"step {name} failed: {res.error}")
                    return 1
        return 0

raise SystemExit(asyncio.run(main()))
```

### Key patterns and gotchas

- **Two context managers with distinct roles:**
  - Outer `async with Orchestral(config=...) as orch:` owns teardown (`await orch.shutdown()` on exit).
  - Inner `with orch as workflow:` calls `orch.create()` (resets prior state, returns a fresh `Workflow`) and intentionally does **not** shut down on exit so you can call `await orch.run(...)` afterward.
- **Pass callables, never coroutines:** `group.add_task(fn, arg1, kw=val)` validates eagerly and rejects already-instantiated coroutine objects (`fn()`).
- **Streaming group results live:** run non-blocking with `await orch.run(wait=False, fail_fast=True)` and iterate `async for batch in orch:` to consume each completed group's `list[ShellProcess | TaskRun]` as it finishes—great for progress logging or incremental reporting.
- **Fail-fast vs. run-to-completion:**
  - `fail_fast=True` cancels in-flight siblings in the active group, skips remaining groups, sets `orch.status == WorkflowStatus.FAILED`, and populates `orch.error` with `OrchestralTaskFailure(error, trace, task_name=..., run_id=...)`.
  - `fail_fast=False` (default) lets all steps finish; inspect `orch.results[alias][run_id].status` on every step so silent failures don't slip past.
- **Timeouts and cancellation:** set per-step `timeout="30s"` and workflow-wide `timeout="10m"` (accepts seconds or duration strings like `"500ms"`, `"1m30s"`). Use `await orch.stop()` to cancel cleanly or `orch.abort()` for immediate synchronous teardown (`SIGKILL` to process groups).
- **Env gotcha on `add_command`:** `env=...` replaces the child env; merge with `{**os.environ, ...}` if inheriting.

## Managing orchestral automation

- Map topological layers from **dagify** directly into `workflow.group()` stages, keeping steps touching different files in the same group (**no-shared-writes**).
- Always check both `orch.status` and per-step `RunStatus` and exit non-zero on failure.
- When you need a full named-dependency DAG, `.werkflow.json` configs, interactive prompts, or built-in git/GitHub/Docker/AWS/Jira/secrets integrations, step up to **werkflow**.

Referenced skills: `dagify` (`../dagify/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `werkflow` (`../werkflow/SKILL.md`). Read any cited skill file before acting when its trigger applies.
