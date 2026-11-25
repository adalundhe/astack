---
name: orchestral
description: "Author, pause, resume, and recover concurrent Python/shell DAG wave pipelines with SQLite checkpoints. Use for parallel build/test/benchmark DAGs and resumable automation."
disable-model-invocation: true
---

# Orchestral

Build concurrent DAG wave and multi-stage pipelines mixing shell commands, `async def` coroutines, and sync functions. Powered by `orchestral` (`https://github.com/adalundhe/orchestral`, on `taskex >= 0.5.0`, Python >= 3.11) with live pause/resume and SQLite recovery.

## Setup and execution

- Check `automation.mode` in `~/.config/astack/settings.json` first. Never install the Python stack under `agentic-only`; use agentic orchestration instead.
- Verify availability with `astack-tools doctor` (`orchestral_dag` and `orchestral_checkpoints`). Install via `astack-tools install`, or `uv add orchestral` inside a Python project.
- Run standalone scripts via `astack-tools python <script.py>` (or `eval "$(astack-tools env)"`).

## Execution model & core API

Two composable ordering tools:

1. **DAG waves (preferred):** declare `dependencies=[...]` on steps. `orchestral` validates the DAG upfront (`build_execution_plan`) and runs parallel waves automatically.
2. **Sequential groups (`workflow.group()`):** add hard stage barriers when stage `k` must finish before stage `k + 1` starts.

Primary `taskex` models and helpers (`Env`, `RunStatus`, `SQLiteCheckpointStore`, `checkpoint`, `pause_point`, `last_checkpoint`) are re-exported directly from `orchestral`.

```python
import asyncio
from orchestral import (
    Env, Orchestral, RunStatus, SQLiteCheckpointStore, WorkflowStatus,
    checkpoint, last_checkpoint, pause_point,
)

async def transform_records(items: list[str]) -> list[str]:
    prev = last_checkpoint()
    start = prev.state["idx"] if prev else 0
    done = list(prev.state["done"]) if prev else []
    for i in range(start, len(items)):
        await pause_point()
        done.append(items[i].upper())
        await checkpoint({"idx": i + 1, "done": done})
    return done

async def main() -> int:
    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")  # "none" | "thread" | "process"
    with SQLiteCheckpointStore("./state/workflow.db") as store:
        async with Orchestral(config=config, checkpoint_store=store, workflow_id="release-check") as orch:
            with orch as workflow:
                s_lint = workflow.add_command("ruff", "check", ".", alias="lint", timeout="60s")
                s_unit = workflow.add_command("pytest", "-q", "tests/unit", alias="unit", timeout="2m")
                workflow.add_task(
                    transform_records, ["a", "b", "c"],
                    alias="transform", dependencies=[s_lint, s_unit], timeout="5m",
                )
            print("Waves:", orch.execution_order())
            await orch.run(wait=True, fail_fast=True, timeout="10m")
            if orch.status != WorkflowStatus.COMPLETED:
                print(f"workflow {orch.status.value}: {orch.error}")
                return 1
            for name, runs in orch.results.items():
                for _, res in runs.items():
                    if res.status != RunStatus.COMPLETE:
                        print(f"step {name} ({res.status.value}): {res.error}")
                        return 1
            return 0

raise SystemExit(asyncio.run(main()))
```

### DAG, streaming, and error handling

- **Dependencies (`dependencies=`):** pass `Step` objects, `alias` strings (fan-in), or callables in any order.
- **Upfront validation:** inspect waves with `orch.execution_order()`. Both `run()` and `resume()` validate before starting (`OrchestralGraphError`, `OrchestralCycleError` with `.cycle`), so invalid graphs never partially run.
- **Two context managers:** outer `async with Orchestral(...) as orch:` owns teardown. Inner `with orch as workflow:` builds a fresh workflow without shutting down on exit.
- **Callables only:** pass `fn`, never a coroutine object `fn()`. Use `functools.partial` when parameter names collide with `timeout`, `alias`, or `dependencies`.
- **Failure modes:**
  - `fail_fast=False` (default): skips explicit and transitive dependents (`RunStatus.CANCELLED`) while independent branches finish. Check every step in `orch.results`.
  - `fail_fast=True`: cancels in-flight siblings, skips later waves, sets `WorkflowStatus.FAILED`, and records `orch.error` (`OrchestralTaskFailure`).
- **Streaming:** call `await orch.run(wait=False)` and iterate `async for batch in orch:`, or await `orch.wait()`.
- **Env gotcha:** `add_command(..., env=...)` replaces child env. Merge `{**os.environ, ...}` to preserve `PATH`.

### Checkpointing, pause, and crash recovery

- Give durable workflows a stable `workflow_id` and a `SQLiteCheckpointStore` (or `MERCURY_SYNC_CHECKPOINT_DB_PATH`).
- **Checkpoints:** save progress with `checkpoint()` and inspect via `orch.checkpoint`, `get_checkpoint`, `list_checkpoints`, or `clear_checkpoints` (**checkpoint**).
- **Live pause:** freeze workflows or steps with `orch.pause()` and `pause_step(target)` (**suspend**).
- **Resume & crash recovery:** unpause in place or replay with `orch.resume(rerun_completed=False)` and `add_task(..., resume_from=...)` (**resume**).

## Managing orchestral automation

- Map **dagify** tasks into `add_task`/`add_command` with `dependencies=[...]`, test `orch.execution_order()`, and isolate outputs (**no-shared-writes**).
- Check both `orch.status` and per-step `RunStatus`, exiting non-zero on failure.
- Use `taskex` for standalone tasks/watchers or `werkflow` for `@step` data injection and `werkflow-modules`.

**Done when:** `orch.execution_order()` validates, `orch.status == WorkflowStatus.COMPLETED`, every step finishes `RunStatus.COMPLETE`, and checkpoints replay cleanly.

Referenced skills: `checkpoint` (`../checkpoint/SKILL.md`), `suspend` (`../suspend/SKILL.md`), `resume` (`../resume/SKILL.md`), `dagify` (`../dagify/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`). Read any cited skill file before acting when its trigger applies.
