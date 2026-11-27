#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Background Job Runner

Submits callables to background threads and lets callers await completion in `src/job_runner.py`.

## Public Contract

### `JobRunner(max_workers: int | None = None)`
- `submit(job_id: str, fn: Callable[[], T]) -> str`:
  - Rejects duplicate `job_id` with `ValueError`.
  - Runs `fn()` on a background worker thread and signals completion immediately when `fn()` returns or raises.
  - Returns `job_id`.
- `wait_for(job_id: str, timeout: float | None = None) -> T`:
  - Raises `KeyError` immediately if `job_id` is unknown.
  - Wakes directly on completion/failure notification (must **not** poll using `time.sleep`).
  - Returns the callable's result on success, or re-raises the original exception on failure.
  - Raises `TimeoutError` if `timeout` elapses before completion.
- `wait_all(job_ids: list[str], timeout: float | None = None) -> dict[str, Any]`:
  - Validates all `job_ids` exist (raising `KeyError` immediately for any unknown ID).
  - Awaits all requested jobs under a single shared deadline when `timeout` is set (raising `TimeoutError` if the deadline expires, or re-raising if any job fails).
  - Returns `{job_id: result}` for all requested IDs.
- `shutdown(wait: bool = True) -> None`:
  - Shuts down background worker threads.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/job_runner.py <<'EOF'
from __future__ import annotations

import threading
import time
from typing import Any, Callable


class JobRunner:
    """Runs background callables and polls for completion using fixed sleeps."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._lock = threading.Lock()
        self._results: dict[str, Any] = {}
        self._errors: dict[str, BaseException] = {}
        self._done: set[str] = set()
        self._known: set[str] = set()
        self._threads: list[threading.Thread] = []

    def submit(self, job_id: str, fn: Callable[[], Any]) -> str:
        with self._lock:
            if job_id in self._known:
                raise ValueError(f"duplicate job_id: {job_id}")
            self._known.add(job_id)

        def _worker() -> None:
            try:
                value = fn()
            except BaseException as exc:
                with self._lock:
                    self._errors[job_id] = exc
                    self._done.add(job_id)
            else:
                with self._lock:
                    self._results[job_id] = value
                    self._done.add(job_id)

        thread = threading.Thread(target=_worker, daemon=True)
        with self._lock:
            self._threads.append(thread)
        thread.start()
        return job_id

    def wait_for(self, job_id: str, timeout: float | None = None) -> Any:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                if job_id in self._done:
                    if job_id in self._errors:
                        raise self._errors[job_id]
                    return self._results[job_id]
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for job {job_id}")
            time.sleep(0.2)

    def wait_all(self, job_ids: list[str], timeout: float | None = None) -> dict[str, Any]:
        deadline = None if timeout is None else time.monotonic() + timeout
        results: dict[str, Any] = {}
        for job_id in job_ids:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            results[job_id] = self.wait_for(job_id, timeout=remaining)
        return results

    def shutdown(self, wait: bool = True) -> None:
        if wait:
            for thread in list(self._threads):
                thread.join()
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_job_runner.py <<'EOF'
import unittest

from src.job_runner import JobRunner


class JobRunnerBasicTest(unittest.TestCase):
    def test_submit_and_wait_for_returns_result(self):
        runner = JobRunner()
        try:
            runner.submit("job-1", lambda: 21 * 2)
            self.assertEqual(runner.wait_for("job-1", timeout=2.0), 42)
        finally:
            runner.shutdown()


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
