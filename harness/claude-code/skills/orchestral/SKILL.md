---
name: orchestral
description: "Author, run, pause, resume, and recover DAG wave and multi-stage concurrent Python/shell workflows with SQLite checkpointing using orchestral. Use for parallel build/test/benchmark DAGs and resumable automation."
disable-model-invocation: true
---

# Orchestral

Build and manage DAG wave and multi-stage concurrent pipelines mixing shell commands, `async def` coroutines, and sync functions—with live pause/resume and SQLite crash recovery—using `orchestral` (`https://github.com/adalundhe/orchestral`, built on `taskex >= 0.5.0`, Python >= 3.11).

## Setup and execution

- Verify availability with `astack-tools doctor` (`orchestral_dag` and `orchestral_checkpoints`). Install or upgrade via `astack-tools install`, or `uv add orchestral` inside a Python project.
- Run standalone scripts via `astack-tools python <script.py>` (or `eval "$(astack-tools env)"`).

## Execution model & core API

Two composable ordering tools:

1. **DAG waves (preferred):** declare `dependencies=[...]` on steps. `orchestral` validates the DAG upfront (`build_execution_plan`) and runs parallel waves automatically.
2. **Sequential groups (`workflow.group()`):** add hard stage barriers when stage `k` must finish before stage `k + 1` starts.

Primary `taskex` models and helpers (`Env`, `RunStatus`, `SQLiteCheckpointStore`, `checkpoint`, `pause_point`, `last_checkpoint`, etc.) are re-exported directly from `orchestral`.

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
    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")
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

- **Dependencies (`dependencies=`):** accepts `Step` objects, `alias` strings (fan-in), or callables in any declaration order.
- **Upfront validation:** call `orch.execution_order()` to inspect waves. `run()` and `resume()` validate before starting any step (`OrchestralGraphError` for missing deps; `OrchestralCycleError` with `.cycle` for cycles), so invalid graphs never partially execute.
- **Two context managers:** outer `async with Orchestral(...) as orch:` owns teardown; inner `with orch as workflow:` builds a fresh workflow without shutting down on exit.
- **Callables only:** pass `fn`, never a coroutine object `fn()`. Use `functools.partial` if a parameter name collides with `add_task` options (`timeout`, `alias`, `dependencies`).
- **Failure modes:**
  - `fail_fast=False` (default): skips only explicit and transitive dependents (`RunStatus.CANCELLED`) while independent branches keep running. Check every step in `orch.results`.
  - `fail_fast=True`: cancels in-flight siblings, skips later waves, sets `WorkflowStatus.FAILED`, and populates `orch.error` (`OrchestralTaskFailure`).
- **Streaming:** run `await orch.run(wait=False)` and iterate `async for batch in orch:`, or await `orch.wait()`.
- **Env gotcha:** `add_command(..., env=...)` replaces child env; merge with `{**os.environ, ...}` to preserve `PATH`.

### Checkpointing, pause, and crash recovery

- **Stores & `workflow_id`:** give durable workflows a stable `workflow_id`. Persist via `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH=...)` or a caller-managed `SQLiteCheckpointStore(...)`.
- **Live pause (`WorkflowStatus.PAUSED`):** `await orch.pause()` freezes timeouts, pauses active tasks and POSIX subprocesses (`SIGSTOP`), blocks later waves, and saves a checkpoint. `await orch.resume(wait=...)` continues cleanly. Use `pause_step(target)` and `resume_step(target)` to pause one step while siblings keep running.
- **Crash recovery:** call `await orch.resume(wait=True, rerun_completed=False)` in a fresh `Orchestral` sharing the same store and `workflow_id`. Completed steps are skipped and restored; remaining steps resume from their latest `last_checkpoint()`.
- **External API:** `add_task(..., resume_from=...)` plus `orch.checkpoint`, `get_checkpoint`, `list_checkpoints`, and `clear_checkpoints`.

## Managing orchestral automation

- Map **dagify** tasks into `add_task`/`add_command` with `dependencies=[...]`, test `orch.execution_order()`, and avoid shared writes (**no-shared-writes**).
- Check both `orch.status` and per-step `RunStatus`, exiting non-zero on failure.
- See **checkpoint**, **suspend**, and **resume** for playbooks; use **taskex** for standalone tasks/watchers or **werkflow** for `@step` data injection and `werkflow-modules`.

Referenced skills: `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `no-shared-writes` (`${CLAUDE_SKILL_DIR}/../no-shared-writes/SKILL.md`), `checkpoint` (`${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`), `suspend` (`${CLAUDE_SKILL_DIR}/../suspend/SKILL.md`), `resume` (`${CLAUDE_SKILL_DIR}/../resume/SKILL.md`), `taskex` (`${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`), `werkflow` (`${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`). Read any cited skill file before acting when its trigger applies.
