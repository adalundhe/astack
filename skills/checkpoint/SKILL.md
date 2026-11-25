---
name: checkpoint
description: "Instrument, save, inspect, and verify durable checkpoints for taskex tasks and orchestral workflows using SQLiteCheckpointStore and ContextVar helpers. Use when making long-running automation crash-resumable."
disable-model-invocation: true
---

# Checkpoint

Save, inspect, and verify durable checkpoints in `taskex` tasks and `orchestral` workflows so runs survive interruptions without repeating completed work.

## 1. Check the runtime

Run `astack-tools doctor` to confirm `taskex_checkpoints: true` and `orchestral_checkpoints: true` (upgrade via `astack-tools install` if missing). If `automation.mode` is `"agentic-only"`, persist progress with atomic state files or git commits per **safe-to-rerun** instead.

## 2. Configure durable storage

Use `SQLiteCheckpointStore` (stdlib `sqlite3`, WAL mode) for anything that must survive restarts:

- **Caller-managed store (best for cross-restart recovery):**
  ```python
  with SQLiteCheckpointStore("./state/checkpoints.db", max_checkpoints_per_run=50) as store:
      async with Orchestral(config=Env(MERCURY_SYNC_EXECUTOR_TYPE="none"), checkpoint_store=store, workflow_id="daily-etl") as orch:
          ...
  ```
- **Runner-managed SQLite:** `Env(MERCURY_SYNC_CHECKPOINT_DB_PATH="./state/checkpoints.db")` (closed on `shutdown()`/`abort()`).
- **In-memory (tests):** `MemoryCheckpointStore(max_checkpoints_per_run=...)`.
- **Custom backend:** implement `CheckpointStore` (`save`, `get_latest`, `get_latest_for_task`, `list_checkpoints`, `delete`, `close`); sync or async methods work.
- **Payload hygiene:** store compact JSON-serializable cursors, IDs, or paths—never secrets, raw handles, or giant blobs.

## 3. Instrument tasks without changing signatures

Both `taskex` and `orchestral` export `checkpoint`, `checkpoint_sync`, `pause_point`, `pause_point_sync`, `last_checkpoint`, and `get_run_context`:

- **Async tasks (`async def`):** load `prev = last_checkpoint()` on entry, call `await pause_point()` before each unit, and call `await checkpoint(state, metadata=..., check_pause=True)` after each unit.
- **Sync tasks (`"thread"` / `"none"`):** use `last_checkpoint()`, `pause_point_sync()`, and `checkpoint_sync(...)`.
- **`"process"` tasks or shell commands:** `ContextVar` cannot cross OS processes. Call `await runner.checkpoint(token, state)` or `await orch.checkpoint(target, state)` externally, or switch to `"thread"` / `"none"`.

## 4. Inspect and manage checkpoints

- **`taskex`:** `get_checkpoint(token)`, `get_latest_task_checkpoint(task_name)`, `list_checkpoints(token)`, and `clear_checkpoints(token)`.
- **`orchestral`:** `get_checkpoint(target)`, `list_checkpoints(token)`, and `clear_checkpoints(target=None)` (`None` clears the workflow), plus automatic wave checkpoints keyed by `workflow_id`.
- Result snapshots expose `res.checkpoint` and `res.paused_duration`.

## 5. Verify durability (**prove-it**, **safe-to-rerun**)

Run partway, assert stored checkpoint state matches the last unit, kill mid-run, and confirm **resume** continues from that state with zero duplicate side effects. Pair with **taskex**, **orchestral**, and **suspend**.
