#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/sync.py <<'EOF'
"""Incremental sync helpers."""
from __future__ import annotations


def normalize_batch(records: list[str]) -> list[str]:
    return [r.strip() for r in records if r.strip()]
EOF

cat > repo/tests/test_sync.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sync import normalize_batch


class SyncTest(unittest.TestCase):
    def test_normalize_batch(self):
        self.assertEqual(normalize_batch([" a ", "", "b"]), ["a", "b"])
EOF

git -C repo add .
git -C repo commit -q -m "initial sync module"

git -C repo checkout -q -b lane/sync
git -C repo rev-parse HEAD > program/pre_suspend_sha.txt

# Leave green uncommitted WIP edits on lane/sync
cat > repo/src/sync.py <<'EOF'
"""Incremental sync helpers."""
from __future__ import annotations


def normalize_batch(records: list[str]) -> list[str]:
    return [r.strip() for r in records if r.strip()]


def checkpoint_offset(offset: int, processed: int) -> int:
    """Advance a sync cursor offset monotonically."""
    if offset < 0 or processed < 0:
        raise ValueError("offset and processed must be non-negative")
    return offset + processed
EOF

cat > repo/tests/test_sync.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sync import checkpoint_offset, normalize_batch


class SyncTest(unittest.TestCase):
    def test_normalize_batch(self):
        self.assertEqual(normalize_batch([" a ", "", "b"]), ["a", "b"])

    def test_checkpoint_offset(self):
        self.assertEqual(checkpoint_offset(10, 5), 15)
        with self.assertRaises(ValueError):
            checkpoint_offset(-1, 2)
EOF

cat > program/settings.json <<'EOF'
{
  "automation": {
    "mode": "agentic-only"
  }
}
EOF

cat > program/LANES.md <<'EOF'
<!-- astack lane log -->
# Sync Program

Repository: ./repo

## Plan
- Step 1: Implement `checkpoint_offset` cursor helper in `src/sync.py` with unit tests.
- Step 2: Add retry cap in `src/sync.py` with unit tests.

## Log
2026-11-26T08:00Z started w1 on lane/sync (agent worker-1) | branch lane/sync | wind-down 2026-11-26T08:50Z | ends 2026-11-26T09:00Z
EOF
