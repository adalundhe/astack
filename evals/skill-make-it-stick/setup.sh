#!/bin/bash
set -euo pipefail
mkdir -p program/astack_home repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/events.py <<'EOF'
"""Event envelope builder."""
from __future__ import annotations

from datetime import datetime


def record_event(kind: str, payload: dict) -> dict:
    """Build an event envelope with a UTC timestamp."""
    return {
        "kind": kind,
        "payload": dict(payload),
        "occurred_at": datetime.now().isoformat(),
    }
EOF

cat > repo/src/other.py <<'EOF'
"""Worker heartbeat timestamp helper."""
from __future__ import annotations

from datetime import datetime, timezone


def heartbeat_ts() -> str:
    """Return a UTC-aware ISO-8601 timestamp for worker heartbeats."""
    return datetime.now(timezone.utc).isoformat()
EOF

cat > repo/tests/test_events.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from events import record_event


class EventsTest(unittest.TestCase):
    def test_record_event_shape(self):
        ev = record_event("signup", {"user": "u1"})
        self.assertEqual(ev["kind"], "signup")
        self.assertEqual(ev["payload"], {"user": "u1"})
        self.assertIn("occurred_at", ev)
EOF

git -C repo add .
git -C repo commit -q -m "initial events and heartbeat modules"

cat > program/incident.md <<'EOF'
# Recurring Incident: Naive Local Timestamps in Production

This is the third time this quarter that a module under `repo/src/` called naive
`datetime.now()` (without a timezone argument) instead of UTC-aware
`datetime.now(timezone.utc)`.

## Impact
- `repo/src/events.py` emitted naive timestamps lacking a UTC offset (`+00:00` / `Z`).
- Warehouse ingestion mis-ordered events across UTC and US-West workers.

## Required Outcome
1. Fix `repo/src/events.py` so `record_event()` produces a UTC-aware ISO timestamp.
2. Add an automated structural AST/static guard test under `repo/tests/` that inspects
   every Python file under `repo/src/` and fails whenever naive `datetime.now()`
   (with no timezone argument) appears in source code.
EOF
