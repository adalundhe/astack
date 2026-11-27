#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/metrics.py <<'EOF'
"""Low-churn read-only counters helper."""
from __future__ import annotations


def success_rate(ok: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return ok / total
EOF

cat > repo/src/cli.py <<'EOF'
"""Thin CLI entrypoint."""
from __future__ import annotations

from src.sync import run_sync_cycle


def main() -> dict[str, object]:
    return run_sync_cycle([{"id": "evt-1", "seq": 1}])
EOF

cat > repo/src/state.py <<'EOF'
"""Local replica state holding a shared mutable dict."""
from __future__ import annotations

_SHARED_STATE: dict[str, object] = {
    "cursor": 0,
    "pending": [],
    "dirty": False,
}


def checkpoint() -> int:
    from src.sync import flush_pending

    if _SHARED_STATE["dirty"]:
        flush_pending()
    return int(_SHARED_STATE["cursor"])
EOF

cat > repo/src/sync.py <<'EOF'
"""Remote delta sync coupled directly to state internals."""
from __future__ import annotations

from src.state import _SHARED_STATE, checkpoint


def flush_pending() -> int:
    pending = _SHARED_STATE["pending"]
    assert isinstance(pending, list)
    flushed = len(pending)
    pending.clear()
    _SHARED_STATE["dirty"] = False
    return flushed


def run_sync_cycle(events: list[dict[str, object]]) -> dict[str, object]:
    for evt in events:
        _SHARED_STATE["pending"].append(evt)
        _SHARED_STATE["cursor"] = int(evt["seq"])
        _SHARED_STATE["dirty"] = True
    cursor = checkpoint()
    return {"cursor": cursor, "dirty": _SHARED_STATE["dirty"]}
EOF

cat > repo/tests/test_sync.py <<'EOF'
import unittest
from src.state import _SHARED_STATE
from src.sync import run_sync_cycle


class SyncTest(unittest.TestCase):
    def setUp(self):
        _SHARED_STATE["cursor"] = 0
        _SHARED_STATE["pending"] = []
        _SHARED_STATE["dirty"] = False

    def test_sync_updates_cursor(self):
        res = run_sync_cycle([{"id": "e1", "seq": 5}])
        self.assertEqual(res["cursor"], 5)
        self.assertFalse(res["dirty"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "feat: initial sync, state, cli, and metrics modules"

# Commit 2: circular import workaround
cat >> repo/src/state.py <<'EOF'


def apply_delta(seq: int, payload: dict[str, object]) -> None:
    from src.sync import notify_cursor_advanced

    if seq > int(_SHARED_STATE["cursor"]):
        _SHARED_STATE["cursor"] = seq
        _SHARED_STATE["dirty"] = True
        notify_cursor_advanced(seq)
EOF

cat >> repo/src/sync.py <<'EOF'


def notify_cursor_advanced(seq: int) -> None:
    _SHARED_STATE["last_notified_seq"] = seq
EOF
git -C repo add src/state.py src/sync.py
git -C repo commit -q -m "fix(sync,state): defer circular import inside state.apply_delta"

# Commit 3: guard cursor regression from shared dict write
cat >> repo/src/state.py <<'EOF'


def reset_if_stale(min_cursor: int) -> bool:
    if int(_SHARED_STATE["cursor"]) < min_cursor:
        _SHARED_STATE["cursor"] = min_cursor
        _SHARED_STATE["dirty"] = True
        return True
    return False
EOF

cat >> repo/src/sync.py <<'EOF'


def sync_with_floor(events: list[dict[str, object]], floor: int) -> dict[str, object]:
    from src.state import reset_if_stale

    reset_if_stale(floor)
    return run_sync_cycle(events)
EOF
git -C repo add src/state.py src/sync.py
git -C repo commit -q -m "fix(state,sync): guard stale _SHARED_STATE cursor overwritten during sync"

# Commit 4: retry clears shared pending list
cat >> repo/src/state.py <<'EOF'


def pending_count() -> int:
    pending = _SHARED_STATE["pending"]
    return len(pending) if isinstance(pending, list) else 0
EOF

cat >> repo/src/sync.py <<'EOF'


def retry_failed_flush() -> int:
    from src.state import pending_count

    if pending_count() > 0:
        _SHARED_STATE["dirty"] = True
        return flush_pending()
    return 0
EOF
git -C repo add src/state.py src/sync.py
git -C repo commit -q -m "fix(sync,state): repair dirty flag when retrying partial flush on _SHARED_STATE"

# Commit 5: partial flush guard
cat >> repo/src/state.py <<'EOF'


def snapshot_state() -> dict[str, object]:
    return {
        "cursor": _SHARED_STATE["cursor"],
        "dirty": _SHARED_STATE["dirty"],
        "pending_len": pending_count(),
    }
EOF

cat >> repo/src/sync.py <<'EOF'


def sync_status() -> dict[str, object]:
    from src.state import snapshot_state

    return snapshot_state()
EOF
git -C repo add src/state.py src/sync.py
git -C repo commit -q -m "fix(state,sync): avoid ImportError in sync_status via inline import"

# Commit 6: race patch on _SHARED_STATE cursor during checkpoint
cat >> repo/src/state.py <<'EOF'


def mark_clean() -> None:
    _SHARED_STATE["dirty"] = False
EOF

cat >> repo/src/sync.py <<'EOF'


def force_reconcile() -> dict[str, object]:
    from src.state import mark_clean

    flushed = flush_pending()
    mark_clean()
    return {"flushed": flushed, "cursor": _SHARED_STATE["cursor"]}
EOF
git -C repo add src/state.py src/sync.py
git -C repo commit -q -m "fix(sync,state): clear stale dirty flag left by state.checkpoint on _SHARED_STATE"
