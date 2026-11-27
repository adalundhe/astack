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


class TransientSyncError(RuntimeError):
    """Raised when a remote sync call fails transiently."""


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

cat > repo/src/sync.py <<'EOF'
"""Incremental sync helpers."""
from __future__ import annotations


class TransientSyncError(RuntimeError):
    """Raised when a remote sync call fails transiently."""


def normalize_batch(records: list[str]) -> list[str]:
    return [r.strip() for r in records if r.strip()]


def checkpoint_offset(offset: int, processed: int) -> int:
    """Advance a sync cursor offset monotonically."""
    if offset < 0 or processed < 0:
        raise ValueError("offset and processed must be non-negative")
    return offset + processed


def sync_batch(fetch_fn, items: list, *, max_retries: int = 3) -> list:
    """Fetch each item via fetch_fn(item), retrying TransientSyncError up to max_retries times.

    Total attempts per item = 1 initial attempt + up to max_retries retries.
    Raises ValueError if max_retries < 0.
    If all attempts fail with TransientSyncError, raises the last TransientSyncError.
    """
    # Step 2 pending: currently ignores max_retries and tries a hardcoded 11 attempts.
    results = []
    for item in items:
        last_err = None
        for _ in range(11):
            try:
                results.append(fetch_fn(item))
                last_err = None
                break
            except TransientSyncError as exc:
                last_err = exc
        if last_err is not None:
            raise last_err
    return results
EOF

cat > repo/tests/test_sync.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sync import checkpoint_offset, normalize_batch, sync_batch


class SyncTest(unittest.TestCase):
    def test_normalize_batch(self):
        self.assertEqual(normalize_batch([" a ", "", "b"]), ["a", "b"])

    def test_checkpoint_offset(self):
        self.assertEqual(checkpoint_offset(10, 5), 15)
        with self.assertRaises(ValueError):
            checkpoint_offset(-1, 2)

    def test_sync_batch_happy_path(self):
        self.assertEqual(sync_batch(lambda x: x * 2, [1, 2, 3]), [2, 4, 6])
EOF

git -C repo commit -q -am "step 1: add checkpoint_offset helper and baseline sync_batch"
STEP1_SHA=$(git -C repo rev-parse HEAD)
echo "${STEP1_SHA}" > program/step1_sha.txt

cat > program/settings.json <<'EOF'
{
  "automation": {
    "mode": "agentic-only"
  }
}
EOF

cat > program/SUSPENDED.md <<EOF
# Suspended Lane: lane/sync

- **Status:** PAUSED
- **Branch:** \`lane/sync\`
- **Saved Commit SHA:** \`${STEP1_SHA}\`
- **Paused At (UTC):** \`2026-11-26T08:30Z\`

## Completed Work (do not repeat)
- Step 1 committed at \`${STEP1_SHA:0:7}\`: implemented \`checkpoint_offset\` in \`repo/src/sync.py\` with unit tests in \`repo/tests/test_sync.py\`.

## Remaining Work
- Step 2: add retry cap enforcement (\`max_retries\`) in \`sync_batch\` inside \`repo/src/sync.py\` plus regression tests in \`repo/tests/test_sync.py\`.

## Verification Command
\`\`\`bash
python3 -B -m unittest discover -s tests
\`\`\`
EOF

cat > program/LANES.md <<EOF
<!-- astack lane log -->
# Sync Program

Repository: ./repo

## Plan
- Step 1 (committed at ${STEP1_SHA:0:7}): \`checkpoint_offset\` cursor helper in \`src/sync.py\` + test.
- Step 2 (remaining): enforce \`max_retries\` retry cap in \`sync_batch\` in \`src/sync.py\` + tests.

## Log
2026-11-26T08:00Z started w1 on lane/sync (agent worker-1) | branch lane/sync | wind-down 2026-11-26T08:50Z | ends 2026-11-26T09:00Z
2026-11-26T08:30Z paused w1 on lane/sync at ${STEP1_SHA:0:7} (step 1 committed; step 2 pending)
EOF
