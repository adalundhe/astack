#!/usr/bin/env bash
set -euo pipefail

mkdir -p program repo/src repo/tests

cat > program/brief.md <<'EOF'
# Job Coordinator Formal Validation & Refactor Brief

## Symptoms Reported

1. **Dual worker ownership (safety violation):**
   After a job times out while running on worker `w1`, worker `w2` can claim and start the same job while `w1` is still recorded as active and can still complete or fail it, leaving two workers holding the job simultaneously (`len(active_workers(job_id)) > 1`).
2. **Unbounded retry livelock (liveness violation):**
   A poisoned job that repeatedly times out bounces between retry and execution indefinitely without ever advancing to `DEAD_LETTER` once `max_retries` attempts are exhausted.

## Required Deliverables

1. **Counterexample capture (`program/counterexample.json`):**
   Capture deterministic counterexample traces from the buggy `./repo/src/coordinator.py` demonstrating BOTH the dual-worker safety violation and the unbounded retry livelock.
2. **Exhaustive BFS state-space checker (`program/check_protocol.py`):**
   Deterministically explore reachable states of `./repo/src/coordinator.py` (using its public API `JobCoordinator`: `submit`, `claim`, `start`, `fail`, `timeout`, `retry`, `complete`, `active_workers`, `get_state`) and check:
   - **Safety:** `len(active_workers(job_id)) <= 1` in every reachable state, and terminal states (`COMPLETED`, `DEAD_LETTER`) have no outgoing transitions.
   - **Liveness:** no reachable infinite retry cycle; once `attempts >= max_retries`, failed/timed-out jobs transition to `DEAD_LETTER` rather than bouncing forever.
   Exit 0 iff zero violations exist, non-zero otherwise.
3. **Explicit state machine (`./repo/src/coordinator.py`):**
   Eliminate the 4 overlapping booleans (`claiming`, `running`, `retrying`, `timed_out`) and replace them with an explicit `Enum` (`JobState`: `QUEUED`, `CLAIMED`, `RUNNING`, `RETRY_WAIT`, `COMPLETED`, `DEAD_LETTER`) with centralized transition validation.
4. **State diagram (`program/STATES.md`):**
   Include a fenced Mermaid `stateDiagram-v2` matching the verified states and transitions.
5. **Comprehensive tests (`./repo/tests/test_coordinator.py`):**
   Cover valid transitions, illegal transition rejection, safety counterexample replay, livelock exhaustion to `DEAD_LETTER`, and multi-step randomized/exhaustive paths.
EOF

cat > repo/src/__init__.py <<'EOF'
"""Job coordinator package."""
EOF

cat > repo/src/coordinator.py <<'EOF'
"""Job coordinator (BUGGY: 4 overlapping booleans allow dual ownership and livelock)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _JobRecord:
    job_id: str
    claiming: bool = False
    running: bool = False
    retrying: bool = False
    timed_out: bool = False
    completed: bool = False
    dead_letter: bool = False
    active_workers: set[str] = field(default_factory=set)
    attempts: int = 0
    max_retries: int = 3


class JobCoordinator:
    def __init__(self, max_retries: int = 3) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        self._max_retries = max_retries
        self._jobs: dict[str, _JobRecord] = {}

    def submit(self, job_id: str) -> None:
        if job_id in self._jobs:
            raise ValueError(f"duplicate job: {job_id}")
        self._jobs[job_id] = _JobRecord(job_id=job_id, max_retries=self._max_retries)

    def _get(self, job_id: str) -> _JobRecord:
        if job_id not in self._jobs:
            raise KeyError(f"unknown job: {job_id}")
        return self._jobs[job_id]

    def claim(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.completed or job.dead_letter:
            return False
        # BUG: allows claiming while timed_out even though previous worker is still running/active!
        if not job.claiming and (not job.running or job.timed_out):
            job.claiming = True
            job.retrying = False
            job.timed_out = False
            job.active_workers.add(worker_id)
            return True
        return False

    def start(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.claiming and worker_id in job.active_workers:
            job.claiming = False
            job.running = True
            job.attempts += 1
            return True
        return False

    def timeout(self, job_id: str) -> bool:
        job = self._get(job_id)
        if job.running:
            # BUG 1: does not clear job.running or remove previous active worker!
            # BUG 2: sets timed_out + retrying without enforcing max_retries -> livelock!
            job.timed_out = True
            job.retrying = True
            return True
        return False

    def fail(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.running and worker_id in job.active_workers:
            job.running = False
            job.active_workers.discard(worker_id)
            if job.attempts >= job.max_retries:
                job.dead_letter = True
            else:
                job.retrying = True
            return True
        return False

    def retry(self, job_id: str) -> bool:
        job = self._get(job_id)
        if job.retrying:
            job.retrying = False
            # BUG: resets attempts on timeout retry so job bounces forever!
            if job.timed_out:
                job.attempts = 0
            return True
        return False

    def complete(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.running and worker_id in job.active_workers:
            job.running = False
            job.timed_out = False
            job.retrying = False
            job.completed = True
            job.active_workers.clear()
            return True
        return False

    def active_workers(self, job_id: str) -> set[str]:
        return set(self._get(job_id).active_workers)

    def attempts(self, job_id: str) -> int:
        return self._get(job_id).attempts

    def get_state(self, job_id: str) -> str:
        job = self._get(job_id)
        if job.completed:
            return "COMPLETED"
        if job.dead_letter:
            return "DEAD_LETTER"
        if job.running:
            return "RUNNING"
        if job.claiming:
            return "CLAIMED"
        if job.retrying:
            return "RETRY_WAIT"
        return "QUEUED"
EOF

cat > repo/tests/test_coordinator.py <<'EOF'
"""Baseline happy-path test (misses safety and livelock bugs)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator import JobCoordinator


class HappyPathCoordinatorTests(unittest.TestCase):
    def test_happy_path_submit_claim_start_complete(self) -> None:
        coord = JobCoordinator(max_retries=2)
        coord.submit("job-1")
        self.assertTrue(coord.claim("job-1", "w1"))
        self.assertTrue(coord.start("job-1", "w1"))
        self.assertEqual(coord.active_workers("job-1"), {"w1"})
        self.assertTrue(coord.complete("job-1", "w1"))
        self.assertEqual(coord.active_workers("job-1"), set())


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo init -q -b main
git -C repo config user.name "Eval Fixture"
git -C repo config user.email "eval@example.invalid"
git -C repo add .
git -C repo commit -q -m "chore: initial boolean-flag job coordinator"
git -C repo rev-parse HEAD > program/base_sha.txt
