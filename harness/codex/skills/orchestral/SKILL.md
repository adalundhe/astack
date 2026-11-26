---
name: orchestral
description: "Turn prompts into saved Orchestral DAG workflows with checkpoints, or run, pause, resume, and manage them. Use for concise shell or Python DAG automation."
---

# Orchestral

Turn a prompt or task graph into a saved Orchestral DAG workflow—or inspect, run, pause, resume, update, and manage existing ones. Powered by `orchestral` (`https://github.com/adalundhe/orchestral`, on `taskex >= 0.5.0`, Python >= 3.11) with live pause/resume and SQLite recovery.

**When to choose Orchestral:** reach for Orchestral for shorter, scriptish DAG workflows—concise shell or stdlib-Python graph tools that need parallel waves and checkpoints without Werkflow's full module and state-passing machinery. Orchestral runs the DAG waves while leaving state-passing, custom skipping, and conditional logic to your step code.

## Storage, setup, and lifecycle (cross-OS)

- **Canonical path:** `$HOME/.astack/<project_name>/automations/<automation_name>/` (`%USERPROFILE%\.astack\<project_name>\automations\<automation_name>\` on Windows; `ASTACK_HOME` overrides). Keep scripts inside a git repo only when explicitly requested.
- Resolve and create folders via `astack-tools automations path <project_name> <automation_name> --ensure`. List saved workflows via `astack-tools automations list [--project <project_name>] --runner orchestral [--json]`.
- Check `automation.mode` in `~/.config/astack/settings.json` and run `astack-tools doctor --json` (`orchestral_dag` and `orchestral_checkpoints`). Under `agentic-only`, ask permission before installing Python packages or running **setup**.
- Under `python-stack`, install via `astack-tools install`, or `uv add orchestral` inside a Python project. Run scripts via `astack-tools python "<automation_dir>/workflow.py"` (or `eval "$(astack-tools env)"`).
- **Manage by intent:**
  1. **List / inspect:** run `astack-tools automations list --project <project_name> --runner orchestral`, then read `automation.json`, the entrypoint, and `state/` checkpoint status.
  2. **Create from a prompt (or `dagify` graph):** check **rtfm**, **lookup**, and **analyze-environment** first. Clarify only missing targets, failure policy, concurrency, or credentials. Keep logic deterministic in Python and shell steps.
  3. **Run:** validate `orch.execution_order()` first, honor `autonomy` (**decisions-in-plain-words**), and test on a safe or dry-run target before mutating live systems.
  4. **Pause, resume, update, or retire:** delegate live pausing and crash recovery to **checkpoint**, **suspend**, and **resume**. When editing steps, verify compatibility with `state/workflow.db` (or clear/bump `workflow_id`). Confirm before deleting a saved workflow.

## Folder layout

Keep each `<automation_name>/` folder self-contained:

- `automation.json`: metadata (`runner`: `"orchestral"`, `entrypoint`: `"workflow.py"`, `workflow_id`, `description`, `updated` UTC).
- `workflow.py`: exposes CLI flags (`--dry-run`, `--show-waves`, `--resume`, `--clear-checkpoints`, `--fail-fast`) and stores checkpoints at `Path(__file__).resolve().parent / "state" / "workflow.db"`.
- `config.example.json` (if parameterized) without secrets; read credentials from env vars or secret managers (**no-leaked-secrets**).
- `state/`: SQLite checkpoint database (never write secrets into checkpoint payloads).

## Execution model & core API

Two composable ordering tools:

1. **DAG waves (preferred):** declare `dependencies=[...]` on steps. `orchestral` validates the DAG upfront (`build_execution_plan`) and runs parallel waves automatically.
2. **Sequential groups (`workflow.group()`):** add hard stage barriers when stage `k` must finish before stage `k + 1` starts.

Primary `taskex` models and helpers (`Env`, `RunStatus`, `SQLiteCheckpointStore`, `checkpoint`, `pause_point`, `last_checkpoint`) are re-exported directly from `orchestral`.

```python
import asyncio
from pathlib import Path
from orchestral import (
    Env, Orchestral, RunStatus, SQLiteCheckpointStore, WorkflowStatus,
    checkpoint, last_checkpoint, pause_point,
)

STATE_DB = Path(__file__).resolve().parent / "state" / "workflow.db"

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
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")  # "none" | "thread" | "process"
    with SQLiteCheckpointStore(str(STATE_DB)) as store:
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
- **Checkpoints:** save progress inside tasks with `checkpoint()` (or externally via `await orch.checkpoint(target, state)`) and manage them via `orch.get_checkpoint`, `list_checkpoints`, or `clear_checkpoints` (**checkpoint**).
- **Live pause:** freeze workflows or steps with `orch.pause()` and `pause_step(target)` (**suspend**).
- **Resume & crash recovery:** unpause in place or replay with `orch.resume(rerun_completed=False)` and `add_task(..., resume_from=...)` (**resume**).

## Verify and compare

- Map **dagify** tasks into `add_task`/`add_command` with `dependencies=[...]`, test `orch.execution_order()`, and isolate outputs (**no-shared-writes**, **prove-it**, **safe-to-rerun**).
- Check both `orch.status` and per-step `RunStatus`, exiting non-zero on failure.
- Prefer **taskex** for general automations, background task management, schedules, and keep/discard retention, or **werkflow** for composed `werkflow-modules`, implicit state-passing, and multi-workflow pipelines.

**Done when:** the workflow is saved under `$HOME/.astack/<project_name>/automations/<automation_name>/` (or Windows equivalent), `orch.execution_order()` validates, `orch.status == WorkflowStatus.COMPLETED`, every step finishes `RunStatus.COMPLETE`, checkpoints replay without duplicates, and your reply gives exact run and resume commands.

Referenced skills: `setup` (`../astack-setup/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `lookup` (`../lookup/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`), `checkpoint` (`../checkpoint/SKILL.md`), `suspend` (`../suspend/SKILL.md`), `resume` (`../resume/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `dagify` (`../dagify/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`), `taskex` (`../taskex/SKILL.md`), `werkflow` (`../werkflow/SKILL.md`). Read any cited skill file before acting when its trigger applies.
