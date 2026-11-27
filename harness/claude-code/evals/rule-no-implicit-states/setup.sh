#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Job Processor

Tracks background job lifecycle in `src/job_processor.py`.

## Public Contract

### `JobState` (`enum.Enum`)
Explicit named lifecycle states:
- `PENDING` (initial state)
- `RUNNING`
- `PAUSED`
- `COMPLETED`
- `FAILED`

### `JobProcessor`
- Exposes `state: JobState`, `result: str | None`, and `error: str | None`.
- Must not store overlapping lifecycle booleans (`is_started`, `is_paused`, `is_failed`, `is_done`).
- Routes all lifecycle transitions through a centralized transition table/method.
- Valid transitions:
  - `PENDING` --`start()`--> `RUNNING`
  - `RUNNING` --`pause()`--> `PAUSED`
  - `PAUSED` --`resume()`--> `RUNNING`
  - `RUNNING` --`complete(result: str)`--> `COMPLETED` (sets `result`, clears `error`)
  - `RUNNING` --`fail(error: str)`--> `FAILED` (sets `error`, clears `result`)
  - `PAUSED` --`fail(error: str)`--> `FAILED` (sets `error`, clears `result`)
  - `FAILED` --`retry()`--> `RUNNING` (clears `error` and `result`)
- Any other method call in any state is invalid and must raise `ValueError` (or a `ValueError` subclass) without modifying `state`, `result`, or `error`.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/job_processor.py <<'EOF'
from __future__ import annotations


class JobProcessor:
    """Tracks job lifecycle using scattered boolean flags."""

    def __init__(self) -> None:
        self.is_started: bool = False
        self.is_paused: bool = False
        self.is_failed: bool = False
        self.is_done: bool = False
        self.result: str | None = None
        self.error: str | None = None

    def start(self) -> None:
        self.is_started = True
        self.is_failed = False
        self.error = None

    def pause(self) -> None:
        self.is_paused = True

    def resume(self) -> None:
        self.is_paused = False

    def complete(self, result: str) -> None:
        self.is_done = True
        self.is_paused = False
        self.result = result

    def fail(self, error: str) -> None:
        self.is_failed = True
        self.error = error

    def retry(self) -> None:
        self.is_failed = False
        self.is_started = True
        self.error = None
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_job_processor.py <<'EOF'
import unittest

from src.job_processor import JobProcessor


class JobProcessorBasicTest(unittest.TestCase):
    def test_start_and_complete_stores_result(self):
        job = JobProcessor()
        job.start()
        job.complete("artifact-123")
        self.assertEqual(job.result, "artifact-123")
        self.assertIsNone(job.error)

    def test_start_and_fail_stores_error(self):
        job = JobProcessor()
        job.start()
        job.fail("upstream timeout")
        self.assertEqual(job.error, "upstream timeout")
        self.assertIsNone(job.result)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
