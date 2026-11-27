"""Separated offline oracle for `capstone-tlc-statechart-livelock`."""
from __future__ import annotations

import json
from pathlib import Path

_FIXED_COORDINATOR = '''"""Job coordinator backed by an explicit finite state machine."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class JobState(Enum):
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    COMPLETED = "COMPLETED"
    DEAD_LETTER = "DEAD_LETTER"


ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset({JobState.CLAIMED}),
    JobState.CLAIMED: frozenset({JobState.RUNNING}),
    JobState.RUNNING: frozenset({JobState.COMPLETED, JobState.RETRY_WAIT, JobState.DEAD_LETTER}),
    JobState.RETRY_WAIT: frozenset({JobState.QUEUED}),
    JobState.COMPLETED: frozenset(),
    JobState.DEAD_LETTER: frozenset(),
}


@dataclass
class _JobRecord:
    job_id: str
    state: JobState = JobState.QUEUED
    owner: str | None = None
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

    def _transition(self, job: _JobRecord, target: JobState) -> None:
        if target not in ALLOWED_TRANSITIONS[job.state]:
            raise ValueError(f"illegal transition {job.state.value} -> {target.value}")
        job.state = target

    def claim(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.state != JobState.QUEUED or job.owner is not None:
            return False
        self._transition(job, JobState.CLAIMED)
        job.owner = worker_id
        return True

    def start(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.state != JobState.CLAIMED or job.owner != worker_id:
            return False
        self._transition(job, JobState.RUNNING)
        job.attempts += 1
        return True

    def _abort_running(self, job: _JobRecord) -> None:
        job.owner = None
        if job.attempts >= job.max_retries:
            self._transition(job, JobState.DEAD_LETTER)
        else:
            self._transition(job, JobState.RETRY_WAIT)

    def timeout(self, job_id: str) -> bool:
        job = self._get(job_id)
        if job.state != JobState.RUNNING:
            return False
        self._abort_running(job)
        return True

    def fail(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.state != JobState.RUNNING or job.owner != worker_id:
            return False
        self._abort_running(job)
        return True

    def retry(self, job_id: str) -> bool:
        job = self._get(job_id)
        if job.state != JobState.RETRY_WAIT:
            return False
        self._transition(job, JobState.QUEUED)
        return True

    def complete(self, job_id: str, worker_id: str) -> bool:
        job = self._get(job_id)
        if job.state != JobState.RUNNING or job.owner != worker_id:
            return False
        job.owner = None
        self._transition(job, JobState.COMPLETED)
        return True

    def active_workers(self, job_id: str) -> set[str]:
        owner = self._get(job_id).owner
        return {owner} if owner is not None else set()

    def attempts(self, job_id: str) -> int:
        return self._get(job_id).attempts

    def get_state(self, job_id: str) -> JobState:
        return self._get(job_id).state
'''

_FIXED_TESTS = '''"""Full-spectrum tests for JobCoordinator safety, liveness, and transitions."""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from coordinator import JobCoordinator, JobState


class JobCoordinatorTests(unittest.TestCase):
    def test_happy_path_submit_claim_start_complete(self) -> None:
        coord = JobCoordinator(max_retries=2)
        coord.submit("job-1")
        self.assertEqual(coord.get_state("job-1"), JobState.QUEUED)
        self.assertTrue(coord.claim("job-1", "w1"))
        self.assertEqual(coord.get_state("job-1"), JobState.CLAIMED)
        self.assertTrue(coord.start("job-1", "w1"))
        self.assertEqual(coord.get_state("job-1"), JobState.RUNNING)
        self.assertEqual(coord.active_workers("job-1"), {"w1"})
        self.assertTrue(coord.complete("job-1", "w1"))
        self.assertEqual(coord.get_state("job-1"), JobState.COMPLETED)
        self.assertEqual(coord.active_workers("job-1"), set())

    def test_safety_counterexample_replay_single_owner_only(self) -> None:
        coord = JobCoordinator(max_retries=3)
        coord.submit("job-s")
        self.assertTrue(coord.claim("job-s", "w1"))
        self.assertFalse(coord.claim("job-s", "w2"))
        self.assertTrue(coord.start("job-s", "w1"))
        self.assertFalse(coord.claim("job-s", "w2"))
        self.assertTrue(coord.timeout("job-s"))
        self.assertEqual(coord.active_workers("job-s"), set())
        self.assertTrue(coord.retry("job-s"))
        self.assertTrue(coord.claim("job-s", "w2"))
        self.assertTrue(coord.start("job-s", "w2"))
        self.assertEqual(coord.active_workers("job-s"), {"w2"})
        self.assertFalse(coord.complete("job-s", "w1"))
        self.assertFalse(coord.fail("job-s", "w1"))
        self.assertTrue(coord.complete("job-s", "w2"))

    def test_livelock_counterexample_replay_reaches_dead_letter(self) -> None:
        coord = JobCoordinator(max_retries=2)
        coord.submit("job-l")
        for idx in range(2):
            self.assertTrue(coord.claim("job-l", "w1"))
            self.assertTrue(coord.start("job-l", "w1"))
            self.assertTrue(coord.timeout("job-l"))
            if idx == 0:
                self.assertEqual(coord.get_state("job-l"), JobState.RETRY_WAIT)
                self.assertTrue(coord.retry("job-l"))
        self.assertEqual(coord.get_state("job-l"), JobState.DEAD_LETTER)
        self.assertFalse(coord.retry("job-l"))
        self.assertFalse(coord.claim("job-l", "w2"))
        self.assertEqual(coord.active_workers("job-l"), set())

    def test_seeded_fuzz_invariants_across_workers(self) -> None:
        rng = random.Random(42)
        workers = ("w1", "w2", "w3")
        for trial in range(25):
            coord = JobCoordinator(max_retries=3)
            coord.submit("j")
            for _ in range(30):
                op = rng.choice(("claim", "start", "timeout", "fail", "retry", "complete"))
                w = rng.choice(workers)
                if op == "claim":
                    coord.claim("j", w)
                elif op == "start":
                    coord.start("j", w)
                elif op == "timeout":
                    coord.timeout("j")
                elif op == "fail":
                    coord.fail("j", w)
                elif op == "retry":
                    coord.retry("j")
                else:
                    coord.complete("j", w)
                self.assertLessEqual(len(coord.active_workers("j")), 1)
                self.assertLessEqual(coord.attempts("j"), 3)


if __name__ == "__main__":
    unittest.main()
'''

_CHECK_PROTOCOL = '''#!/usr/bin/env python3
"""Exhaustive BFS state-space checker for JobCoordinator safety and liveness."""
from __future__ import annotations

import copy
import enum
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "repo" / "src"))
from coordinator import JobCoordinator

WORKERS = ("w1", "w2")
ACTIONS = (
    ("claim", "w1"),
    ("claim", "w2"),
    ("start", "w1"),
    ("start", "w2"),
    ("timeout", None),
    ("fail", "w1"),
    ("fail", "w2"),
    ("retry", None),
    ("complete", "w1"),
    ("complete", "w2"),
)


def _state_name(coord: JobCoordinator) -> str:
    raw = coord.get_state("j")
    return raw.name if isinstance(raw, enum.Enum) else str(raw)


def _snapshot(coord: JobCoordinator) -> tuple[object, ...]:
    rec = coord._jobs["j"]
    # Capture full observable + internal state so cycles are detected accurately
    fields = []
    for k in sorted(vars(rec)):
        v = getattr(rec, k)
        if isinstance(v, set):
            v = tuple(sorted(v))
        elif isinstance(v, enum.Enum):
            v = v.name
        fields.append((k, v))
    return tuple(fields)


def _apply(coord: JobCoordinator, op: str, worker: str | None) -> bool:
    if op == "claim":
        return coord.claim("j", str(worker))
    if op == "start":
        return coord.start("j", str(worker))
    if op == "timeout":
        return coord.timeout("j")
    if op == "fail":
        return coord.fail("j", str(worker))
    if op == "retry":
        return coord.retry("j")
    if op == "complete":
        return coord.complete("j", str(worker))
    raise ValueError(op)


def main() -> int:
    start = JobCoordinator(max_retries=2)
    start.submit("j")
    start_snap = _snapshot(start)

    queue: deque[tuple[JobCoordinator, list[str]]] = deque([(start, [])])
    visited: dict[tuple[object, ...], list[str]] = {start_snap: []}
    adj: dict[tuple[object, ...], set[tuple[object, ...]]] = {start_snap: set()}

    safety_violations: list[str] = []
    terminal_violations: list[str] = []

    while queue:
        cur, trace = queue.popleft()
        cur_snap = _snapshot(cur)
        cur_state = _state_name(cur)

        holders = cur.active_workers("j")
        if len(holders) > 1:
            safety_violations.append(f"dual ownership {sorted(holders)} via {trace}")
            break

        if cur.attempts("j") > 2:
            safety_violations.append(f"attempts exceeded max_retries ({cur.attempts('j')}) via {trace}")
            break

        if len(visited) >= 2000:
            safety_violations.append(f"unbounded state explosion (>={len(visited)} states) via {trace}")
            break

        for op, worker in ACTIONS:
            nxt = copy.deepcopy(cur)
            ok = _apply(nxt, op, worker)
            nxt_snap = _snapshot(nxt)
            if cur_state in ("COMPLETED", "DEAD_LETTER") and (ok or nxt_snap != cur_snap):
                terminal_violations.append(f"terminal state {cur_state} accepted {op}({worker}) via {trace}")
            if not ok or nxt_snap == cur_snap:
                continue
            adj.setdefault(cur_snap, set()).add(nxt_snap)
            if nxt_snap not in visited:
                label = f"{op}({worker})" if worker else op
                visited[nxt_snap] = [*trace, label]
                adj.setdefault(nxt_snap, set())
                queue.append((nxt, visited[nxt_snap]))

    # Liveness check: directed cycle detection (any cycle implies non-terminating livelock)
    color: dict[tuple[object, ...], int] = {node: 0 for node in adj}
    cycles: list[list[str]] = []

    def dfs(node: tuple[object, ...]) -> None:
        color[node] = 1
        for nxt in adj.get(node, ()):
            if color.get(nxt, 0) == 1:
                cycles.append(visited[nxt])
            elif color.get(nxt, 0) == 0:
                dfs(nxt)
        color[node] = 2

    for node in adj:
        if color[node] == 0:
            dfs(node)

    if safety_violations or terminal_violations or cycles:
        print(
            f"VIOLATIONS: safety={len(safety_violations)} terminal={len(terminal_violations)} "
            f"livelock_cycles={len(cycles)}",
            file=sys.stderr,
        )
        return 1

    print(f"OK: explored {len(visited)} reachable states, 0 safety violations, 0 livelock cycles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

_STATES_MD = """# Job Coordinator State Machine

Grounded in `./repo/src/coordinator.py` (`JobState` and `ALLOWED_TRANSITIONS`).

```mermaid
stateDiagram-v2
    [*] --> QUEUED : submit(job_id)
    QUEUED --> CLAIMED : claim(job_id, worker_id)
    CLAIMED --> RUNNING : start(job_id, worker_id) [attempts += 1]
    RUNNING --> COMPLETED : complete(job_id, worker_id)
    RUNNING --> RETRY_WAIT : fail / timeout [attempts < max_retries, owner cleared]
    RUNNING --> DEAD_LETTER : fail / timeout [attempts >= max_retries, owner cleared]
    RETRY_WAIT --> QUEUED : retry(job_id)
    COMPLETED --> [*]
    DEAD_LETTER --> [*]
```

## Verified Invariants

- **Safety (mutual exclusion):** At most one worker owns a job (`len(active_workers(job_id)) <= 1`), and stale workers cannot complete or fail a job after timeout/reclaim.
- **Terminal immutability:** `COMPLETED` and `DEAD_LETTER` have zero outgoing transitions.
- **Liveness (bounded retries):** Every `RUNNING -> RETRY_WAIT` or `RUNNING -> DEAD_LETTER` increments monotonic `attempts`; once `attempts >= max_retries`, the job transitions strictly to `DEAD_LETTER`, eliminating retry livelock cycles.
"""


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "coordinator.py").write_text(_FIXED_COORDINATOR, encoding="utf-8")
    (repo / "tests" / "test_coordinator.py").write_text(_FIXED_TESTS, encoding="utf-8")

    checker = ws / "program" / "check_protocol.py"
    checker.write_text(_CHECK_PROTOCOL, encoding="utf-8")
    checker.chmod(0o755)

    (ws / "program" / "STATES.md").write_text(_STATES_MD, encoding="utf-8")

    counterexample = {
        "model": "repo/src/coordinator.py (root commit)",
        "violated": True,
        "safety": {
            "invariant": "len(active_workers(job_id)) <= 1",
            "violated": True,
            "steps": [
                {"action": "submit(j)", "active_workers": []},
                {"action": "claim(j, w1)", "active_workers": ["w1"]},
                {"action": "start(j, w1)", "active_workers": ["w1"]},
                {"action": "timeout(j)", "active_workers": ["w1"], "note": "w1 not revoked; timed_out=True"},
                {"action": "claim(j, w2)", "active_workers": ["w1", "w2"], "violation": "dual ownership"},
            ],
        },
        "livelock": {
            "invariant": "attempts >= max_retries transitions to DEAD_LETTER with no infinite retry cycle",
            "violated": True,
            "steps": [
                {"action": "submit(j)", "attempts": 0, "state": "QUEUED"},
                {"action": "claim(j, w1)", "attempts": 0, "state": "CLAIMED"},
                {"action": "start(j, w1)", "attempts": 1, "state": "RUNNING"},
                {"action": "timeout(j)", "attempts": 1, "state": "RUNNING+retrying+timed_out"},
                {"action": "retry(j)", "attempts": 0, "violation": "attempts reset to 0, livelock cycle back to start"},
            ],
        },
    }
    (ws / "program" / "counterexample.json").write_text(
        json.dumps(counterexample, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "final_text": (
            "Replaced overlapping booleans in `repo/src/coordinator.py` with explicit `JobState` enum and centralized transitions, "
            "captured both buggy safety and livelock counterexamples in `program/counterexample.json`, documented the Mermaid "
            "`stateDiagram-v2` in `program/STATES.md`, and verified 0 violations across all reachable states with `program/check_protocol.py`."
        ),
    }
