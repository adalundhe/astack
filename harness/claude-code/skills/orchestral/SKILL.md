---
name: orchestral
description: "Author, run, pause, resume, and recover dependency-graph (DAG) wave and multi-stage concurrent Python/shell workflows with durable SQLite checkpointing using orchestral (Orchestral, dependencies, execution_order, pause/resume, workflow_id, branch-aware skipping, fail_fast, streaming waves). Use for parallel build/test/benchmark DAGs and resumable automation."
disable-model-invocation: true
---

# Orchestral

Author and manage dependency-graph (DAG) wave and multi-stage concurrent pipelines mixing shell commands, `async def` coroutines, and sync Python functions—with live pause/resume and durable checkpoint recovery—using `orchestral` (`https://github.com/adalundhe/orchestral`, built on `taskex >= 0.5.0`, Python >= 3.11).

## Setup and execution

- Check availability and feature support with `astack-tools doctor` (verifies `orchestral_dag` and `orchestral_checkpoints`); install or upgrade via `astack-tools install` (add `--from-github` if PyPI lags `main`), or `uv add orchestral` inside a Python project.
- Run scripts via `astack-tools python <script.py>` (or load the managed `uv` venv with `eval "$(astack-tools env)"`).

## Execution model & core API

`orchestral` supports two composable ordering mechanisms:

1. **Dependency-graph (DAG) waves (preferred for task graphs):** add steps directly to `workflow` with `dependencies=[...]`. Before running any step, `orchestral` validates the DAG (`build_execution_plan`, Kahn's topological sort) and runs parallel waves automatically.
2. **Explicit sequential groups (`workflow.group()`):** add strict stage barriers when every wave in stage `k` must finish before stage `k + 1` starts; steps inside a group may still declare intra-group or earlier-group dependencies.

All primary `taskex` models and checkpoint/pause helpers (`Env`, `RunStatus`, `ShellProcess`, `TaskRun`, `Checkpoint`, `CheckpointStore`, `MemoryCheckpointStore`, `SQLiteCheckpointStore`, `checkpoint`, `checkpoint_sync`, `pause_point`, `pause_point_sync`, `last_checkpoint`, `get_run_context`) are re-exported directly from `orchestral`.

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
    # Pure shell/async workflows spawn no executor when config is omitted; use "thread" for closures/blocking I/O or sync checkpoints
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

            # Inspect and validate planned waves before running: [["lint", "unit"], ["transform"]]
            print("Waves:", orch.execution_order())

            # Use orch.resume(wait=True, ...) instead of run() to recover from a prior failed/cancelled run
            await orch.run(wait=True, fail_fast=True, timeout="10m")

            if orch.status != WorkflowStatus.COMPLETED:
                print(f"workflow {orch.status.value}: {orch.error}")
                return 1
            for name, runs in orch.results.items():
                for run_id, res in runs.items():
                    if res.status != RunStatus.COMPLETE:
                        print(f"step {name} ({res.status.value}): {res.error}")
                        return 1
            return 0

raise SystemExit(asyncio.run(main()))
```

### DAG, streaming, and error-handling patterns

- **Declaring dependencies (`dependencies=`):** accepts a single item or iterable of `Step` objects (exact instance match even with duplicate names), step name/`alias` strings (fan-in across all matching steps), or callable references. Steps within the same DAG or `Group` can be declared in any order.
- **Upfront DAG validation:** call `orch.execution_order()` (or `workflow.build_waves()` / `workflow.build_plan()`) to inspect waves before running. `orch.run()` and `orch.resume()` always validate before launching any step—missing/external/later-group deps raise `OrchestralGraphError`; cycles raise `OrchestralCycleError` (inspect `.cycle`). Zero partial execution on invalid graphs.
- **Two context managers with distinct roles:**
  - Outer `async with Orchestral(config=..., checkpoint_store=..., workflow_id=...) as orch:` owns teardown (`await orch.shutdown()` on exit, closing an owned store).
  - Inner `with orch as workflow:` calls `orch.create()` (resets prior run state, returns a fresh `Workflow` preserving `config` and `checkpoint_store`) and intentionally does **not** shut down on exit.
- **Pass callables, never coroutines:** `add_task(fn, ...)` rejects coroutine objects (`fn()`). If `fn` has a parameter colliding with an `add_task` option (`timeout`, `alias`, `dependencies`, `schedule`, `resume_from`), bind it with `functools.partial`.
- **Failure handling (`fail_fast=False` vs. `fail_fast=True`):**
  - `fail_fast=False` (default): **branch-aware skipping**—if step `A` fails, explicit dependents (and transitive dependents) are skipped (`RunStatus.CANCELLED` naming the failed upstream) while independent branches continue. Always check `orch.results[name][run_id].status` on every step.
  - `fail_fast=True`: cancels in-flight siblings in the active wave, skips remaining waves, emits the failing wave to `async for` consumers, sets `orch.status == WorkflowStatus.FAILED`, and populates `orch.error = OrchestralTaskFailure(..., task_name=..., run_id=...)` and `orch.trace`.
- **Streaming wave results & non-blocking runs:** run with `await orch.run(wait=False)` and iterate `async for batch in orch:` (lossless, ordered, multi-consumer, replayable after `wait=True`, terminates cleanly on errors/timeouts/`stop`/`shutdown`/`abort`), or await completion with `await orch.wait()`.
- **Repeating steps & env gotcha:** steps support `schedule`, `repeat` (`"NEVER"`, positive `int`, or `"ALWAYS"`), `keep`, `max_age`, `keep_policy` (`"COUNT"|"AGE"|"COUNT_AND_AGE"`). On `add_command`, `env=...` replaces the child environment—merge with `{**os.environ, ...}` if inheriting.

### Checkpointing, suspend/pause, and crash recovery

- **Stores & `workflow_id`:** give durable workflows a stable `workflow_id="..."` (defaults to `"default"`). Configure persistence via `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH="./state/checkpoints.db")` (owned/closed by `Orchestral`) or an explicit `checkpoint_store=SQLiteCheckpointStore(...)` / custom sync or async `CheckpointStore` (caller owns close).
- **Live workflow pause/resume (`WorkflowStatus.PAUSED`):**
  - `await orch.pause()` freezes workflow & step timeouts, pauses active async/thread callables, POSIX shell process groups (`SIGSTOP`), and repeating schedules, blocks later waves, and saves a workflow checkpoint (`orch.is_paused`, `orch.paused_duration`, `orch.active_tokens`).
  - `await orch.resume(wait=...)` resumes paused steps (`SIGCONT` / unblocks coroutines & threads) and continues remaining waves.
  - **Single-step pause/resume:** `await orch.pause_step(target)` and `await orch.resume_step(target)` (by `Step`, name/alias, or run token) suspend/resume one step while siblings in the same wave keep running.
  - Stopping/shutting down/aborting while paused safely unblocks sync threads and sends `SIGCONT`+`SIGTERM` to `SIGSTOP`-paused subprocesses.
- **Crash/failure recovery:** calling `await orch.resume(wait=True, fail_fast=..., timeout=..., rerun_completed=False)` when not live-paused—including in a brand-new `Orchestral` process sharing the same `SQLiteCheckpointStore` and `workflow_id`—loads the latest workflow checkpoint, **skips already-completed steps** (restoring their results into `orch.results` unless `rerun_completed=True`), and launches remaining steps seeded with their latest task checkpoints (`last_checkpoint()`). Non-JSON-serializable step return values still record completion safely (`result=None`, `result_serialized=False` in SQLite).
- **Step-level `resume_from` & external checkpoint API:** seed any step directly with `add_task(..., resume_from=token | task_name | checkpoint)` (works with sync and async stores), or manage externally via `await orch.checkpoint(target, state, metadata=...)`, `await orch.get_checkpoint(target)`, `await orch.list_checkpoints(token)`, and `await orch.clear_checkpoints(target=None)` (`None` clears the entire workflow).

## Managing orchestral automation

- Map tasks and edges from **dagify** directly into `workflow.add_task` / `workflow.add_command` with `dependencies=[...]`, assert `orch.execution_order()` in tests, and keep concurrent steps from writing the same files (**no-shared-writes**).
- Always check both `orch.status` and per-step `RunStatus` (catching both `FAILED` and skipped `CANCELLED` steps) and exit non-zero on failure.
- Use **checkpoint**, **suspend**, and **resume** for step-by-step checkpointing, pause, and crash-recovery playbooks. Choose **taskex** for standalone tracked tasks/watchers/schedules without a workflow DAG, or **werkflow** when you need automatic return-value injection between `@step`s, `.werkflow.json`/prompts, or `werkflow-modules` integrations.

Referenced skills: `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `no-shared-writes` (`${CLAUDE_SKILL_DIR}/../no-shared-writes/SKILL.md`), `checkpoint` (`${CLAUDE_SKILL_DIR}/../checkpoint/SKILL.md`), `suspend` (`${CLAUDE_SKILL_DIR}/../suspend/SKILL.md`), `resume` (`${CLAUDE_SKILL_DIR}/../resume/SKILL.md`), `taskex` (`${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`), `werkflow` (`${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`). Read any cited skill file before acting when its trigger applies.
