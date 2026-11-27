"""Separated offline oracle for `skill-rearchitect`."""
from __future__ import annotations

from pathlib import Path

REPORT = """# Rearchitecture Discovery Report

## 1. Git Churn Hotspots
Walking `git log --stat` across `./repo` (6 commits total) shows heavy co-change churn concentrated in one tightly coupled pair:
- `src/sync.py` — 6 commits (every single bugfix touches it alongside `src/state.py`).
- `src/state.py` — 6 commits (100% co-change rate with `src/sync.py`).
- `src/metrics.py` and `src/cli.py` — 1 commit each (stable, zero friction).

## 2. Ranked Candidate Card

### Candidate 1 (Top Pick — Strength: `strong`): Unidirectional StateStore + SyncCoordinator
- **Touched files:** `src/state.py`, `src/sync.py`, `src/cli.py`, `tests/test_sync.py`.
- **Concrete structural friction:**
  1. **Bidirectional circular imports:** `src/sync.py` imports `_SHARED_STATE` and helpers from `src/state.py`, while `src/state.py` performs deferred inline imports (`from src.sync import flush_pending`, `from src.sync import notify_cursor_advanced`) inside functions to dodge `ImportError`.
  2. **Shared mutable global dictionary (`_SHARED_STATE`):** Both modules directly read and mutate `_SHARED_STATE["cursor"]`, `_SHARED_STATE["pending"]`, and `_SHARED_STATE["dirty"]`, causing repeated race/stale-flag bugfixes (`checkpoint`, `retry_failed_flush`, `force_reconcile`).
  3. **Testability friction:** `tests/test_sync.py` must manually reset `_SHARED_STATE` globals in `setUp()` because state cannot be instantiated per test.
- **Target decoupled module boundaries:**
  - `src/state.py` owns an explicit `SyncStateStore` class encapsulating `cursor`, `pending`, and `dirty` (single writer, zero imports from `src/sync.py`). Methods return pure snapshots/events instead of calling back into sync.
  - `src/sync.py` owns `SyncCoordinator(store: SyncStateStore)` orchestrating ingestion, flush, retry, and checkpoint unilaterally on top of `SyncStateStore`.
  - `src/cli.py` constructs `SyncStateStore()` + `SyncCoordinator(store)` at the process boundary.
- **Sanity checks (`yagni`, `no-bolt-ons`, `minimize-state-stores`):** No speculative abstract base classes; one concrete `SyncStateStore` eliminates the duplicated `dirty` flag drift by deriving cleanliness from `len(pending) == 0`.

### Before vs. After Architecture

```mermaid
flowchart LR
  subgraph Before["Before (Circular + Shared Global Dict)"]
    B_CLI[src/cli.py] --> B_SYNC[src/sync.py]
    B_SYNC -->|_SHARED_STATE + helpers| B_STATE[src/state.py]
    B_STATE -->|deferred inline imports| B_SYNC
  end

  subgraph After["After (Acyclic Unidirectional Ownership)"]
    A_CLI[src/cli.py] --> A_SYNC[src/sync.py: SyncCoordinator]
    A_SYNC -->|explicit methods| A_STATE[src/state.py: SyncStateStore]
  end
```

## 3. Incremental Migration Plan
1. **Step 1 — Pin external behavior with tests:** Expand `tests/test_sync.py` to cover `run_sync_cycle`, `sync_with_floor`, `retry_failed_flush`, `force_reconcile`, and `sync_status` without reaching into `_SHARED_STATE`.
2. **Step 2 — Record architecture decision (`create-adc`):** Document `SyncStateStore` ownership and removal of module-global `_SHARED_STATE`.
3. **Step 3 — Introduce `SyncStateStore` in `src/state.py`:** Encapsulate `cursor`, `pending`, and derived `dirty` state with zero imports from `src/sync.py`.
4. **Step 4 — Cut `src/sync.py` over to `SyncCoordinator`:** Route all state mutations through `SyncStateStore` methods, delete deferred inline imports, and keep a temporary default instance only until `src/cli.py` injects its own store.
5. **Step 5 — Trim legacy globals & verify:** Remove `_SHARED_STATE`, update `src/cli.py` and tests to instantiate fresh `SyncStateStore` instances, and run the full test suite + review.
"""


def apply(ws: Path) -> dict[str, object]:
    """Write program/REARCHITECT.md without modifying ./repo."""
    (ws / "program" / "REARCHITECT.md").write_text(REPORT, encoding="utf-8")
    return {
        "final_text": (
            "Wrote rearchitecture discovery report to `program/REARCHITECT.md` without modifying `./repo`. "
            "Git history shows 6 co-change commits across `src/sync.py` and `src/state.py` caused by bidirectional circular imports "
            "and shared mutable `_SHARED_STATE`. Top pick (`strong`): encapsulate state in an acyclic `SyncStateStore` owned by `src/state.py` "
            "with `SyncCoordinator` in `src/sync.py` depending unidirectionally, migrated in 5 incremental steps."
        ),
    }
