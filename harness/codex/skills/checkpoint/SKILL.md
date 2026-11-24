---
name: checkpoint
description: "Instrument, save, inspect, and verify durable checkpoints for taskex tasks and orchestral workflows using SQLiteCheckpointStore and ContextVar helpers (checkpoint, checkpoint_sync, last_checkpoint, pause_point). Use when making long-running automation crash-resumable or inspecting saved progress."
---

# Checkpoint

Save, inspect, and verify durable progress checkpoints in `taskex` tasks and `orchestral` workflows so runs survive interruptions and resume without repeating completed work.

## 1. Check the runtime

Run `astack-tools doctor`.
- Confirm `taskex_checkpoints: true` (for `taskex`) and `orchestral_checkpoints: true` (for `orchestral`; upgrade via `astack-tools install` or `--from-github` if missing).
- If `settings.json` sets `automation.mode` to `"agentic-only"` (or the Python stack is not installed), persist progress with atomic state files or git commits per **safe-to-rerun** instead.

## 2. Configure durable storage (`taskex` and `orchestral`)

Prefer `SQLiteCheckpointStore` (stdlib `sqlite3`, WAL mode) for anything that must survive crashes or restarts:

- **Caller-managed store (recommended for cross-restart inspection & recovery):**
  ```python
  # Works identically for TaskRunner and Orchestral (give Orchestral a stable workflow_id)
  with SQLiteCheckpointStore("./state/checkpoints.db", max_checkpoints_per_run=50) as store:
      async with Orchestral(config=Env(MERCURY_SYNC_EXECUTOR_TYPE="none"), checkpoint_store=store, workflow_id="daily-etl") as orch:
          ...
  ```
- **Runner-managed SQLite:** `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH="./state/checkpoints.db")` (closed automatically on `shutdown()`/`abort()`).
- **In-memory (ephemeral/tests):** `MemoryCheckpointStore(max_checkpoints_per_run=...)` (default).
- **Custom backend:** implement the `CheckpointStore` protocol (`save`, `get_latest`, `get_latest_for_task`, `list_checkpoints`, `delete`, `close`); sync or `async def` methods are supported automatically.
- **Payload discipline:** `SQLiteCheckpointStore` requires JSON-serializable `state` and `metadata` on `checkpoint(...)`. Store compact progress cursors, IDs, or artifact paths—never secrets, raw handles, or giant blobs. (In `orchestral`, non-JSON-serializable step return values still record workflow step completion safely with `result=None` and `result_serialized=False` in SQLite.)

## 3. Instrument tasks without changing signatures

Both `taskex` and `orchestral` export the same `ContextVar` helpers (`checkpoint`, `checkpoint_sync`, `pause_point`, `pause_point_sync`, `last_checkpoint`, `get_run_context`):

- **Async tasks (`async def`):**
  1. At entry, load `prev = last_checkpoint()` and initialize state from `prev.state` if present.
  2. Call `await pause_point()` before starting each unit of work.
  3. Commit each finished unit with `await checkpoint(state, metadata=..., check_pause=True)` (persists first, updates `run.latest_checkpoint`, then honors any pending pause).
- **Sync tasks on `"thread"` or `"none"` executors:** use `last_checkpoint()`, `pause_point_sync()`, and `checkpoint_sync(state, metadata=..., check_pause=True)` (`contextvars.Context` is copied into the worker thread).
- **Sync tasks on `"process"` executor or shell commands:** `ContextVar` cannot cross OS process boundaries. Record checkpoints externally via `await runner.checkpoint(run.token, state, metadata=...)` or `await orch.checkpoint(target, state, metadata=...)` (where `target` is a token, step name/alias, or `Step`), or switch sync workers to `"thread"` / `"none"`.

## 4. Inspect and manage checkpoints

- **In `taskex`:** `await runner.get_checkpoint(token)` (works even in a new `TaskRunner`), `await runner.get_latest_task_checkpoint(task_name)`, `await runner.list_checkpoints(token)`, `await runner.clear_checkpoints(token)`.
- **In `orchestral`:** `await orch.get_checkpoint(target)` (token, step name/alias, or `Step`), `await orch.list_checkpoints(token)`, `await orch.clear_checkpoints(target=None)` (passing `None` clears the entire workflow's checkpoints), plus automatic workflow-level checkpoints recorded on wave completions and `orch.pause()` keyed by `workflow_id`.
- Result snapshots (`TaskRun` / `ShellProcess`) expose `res.checkpoint` and `res.paused_duration`.

## 5. Verify durability

Before trusting checkpoints on real work (**prove-it**, **safe-to-rerun**): run the task or workflow partway, assert stored checkpoint state matches the last committed unit/wave, cancel or kill mid-run, and verify **resume** continues from that exact state with zero duplicate side effects. Pair with **taskex**, **orchestral**, and **suspend**.

Referenced skills: `safe-to-rerun` (`../safe-to-rerun/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `resume` (`../resume/SKILL.md`), `taskex` (`../taskex/SKILL.md`), `orchestral` (`../orchestral/SKILL.md`), `suspend` (`../suspend/SKILL.md`). Read any cited skill file before acting when its trigger applies.
