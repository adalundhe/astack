#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Background Job Queue Worker

Provides `Job`, `MetricsRegistry`, `DeadLetterRecord`, and `JobProcessor` in `src/queue_worker.py`.

## Public API & Requirements
- `Job(job_id: str, job_type: str, user_id: str, request_id: str, payload: dict, trace_id: str | None = None)`
- `MetricsRegistry`:
  - `inc(name: str, labels: dict[str, str] | None = None, value: int = 1)`
  - `set_gauge(name: str, value: float, labels: dict[str, str] | None = None)`
  - `series_count() -> int` (total distinct `(name, sorted_label_items)` series across counters and gauges)
  - `snapshot() -> dict` (`{"counters": {...}, "gauges": {...}}`)
- `DeadLetterRecord(job: Job, error_type: str, error_message: str, trace_id: str, attempts: int)`
- `JobProcessor(handler, *, metrics: MetricsRegistry | None = None, max_attempts: int = 2, log_sink: list[dict] | None = None)`:
  - `dlq: list[DeadLetterRecord]`
  - `last_success_ts: float | None`
  - `process_one(job: Job) -> bool`
  - `process_all(jobs: list[Job]) -> dict`: returns `{"processed": int, "failed": int, "dlq_depth": int}`

### Operational Telemetry Requirements
1. **Bounded metric cardinality**: Metric labels may ONLY use bounded dimensions (`job_type`, `outcome`, `error_type`). Never include unbounded identifiers (`user_id`, `request_id`, `job_id`, `trace_id`, `correlation_id`) in metric labels.
2. **Structured logs with correlation context**: Emit a structured dict per job into `log_sink` including `trace_id` (propagating `job.trace_id` or generating a non-empty trace ID when absent), `job_id`, `job_type`, `outcome`, and (on failure) `error_type`.
3. **No silent drops / Dead-letter queue**: Retry failing jobs up to `max_attempts`. If a job succeeds on retry, do not place it in `dlq`. If all attempts fail, append a `DeadLetterRecord` to `self.dlq`, increment failure metrics, and update the `dlq_depth` gauge.
4. **Heartbeat**: Update `self.last_success_ts` (epoch seconds float) and a heartbeat gauge whenever a job succeeds.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/queue_worker.py <<'EOF'
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Job:
    job_id: str
    job_type: str
    user_id: str
    request_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    trace_id: str | None = None


@dataclass(frozen=True)
class DeadLetterRecord:
    job: Job
    error_type: str
    error_message: str
    trace_id: str
    attempts: int


class MetricsRegistry:
    """In-memory counter and gauge registry."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}

    @staticmethod
    def _key(name: str, labels: dict[str, str] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
        items = tuple(sorted((str(k), str(v)) for k, v in (labels or {}).items()))
        return (name, items)

    def inc(self, name: str, labels: dict[str, str] | None = None, value: int = 1) -> None:
        key = self._key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._key(name, labels)
        self._gauges[key] = float(value)

    def series_count(self) -> int:
        return len(self._counters) + len(self._gauges)

    def snapshot(self) -> dict[str, dict[tuple[str, tuple[tuple[str, str], ...]], float | int]]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
        }


class JobProcessor:
    """Queue worker with high-cardinality metrics, silent drops, and missing trace context."""

    def __init__(
        self,
        handler: Callable[[Job], None],
        *,
        metrics: MetricsRegistry | None = None,
        max_attempts: int = 2,
        log_sink: list[dict[str, Any]] | None = None,
    ) -> None:
        self._handler = handler
        self.metrics = metrics if metrics is not None else MetricsRegistry()
        self.max_attempts = max_attempts
        self.log_sink: list[dict[str, Any]] = log_sink if log_sink is not None else []
        self.dlq: list[DeadLetterRecord] = []
        self.last_success_ts: float | None = None

    def process_one(self, job: Job) -> bool:
        try:
            self._handler(job)
            self.metrics.inc(
                "jobs_processed_total",
                labels={
                    "job_type": job.job_type,
                    "user_id": job.user_id,
                    "request_id": job.request_id,
                    "job_id": job.job_id,
                },
            )
            self.log_sink.append({"event": "job_done", "job_type": job.job_type})
            return True
        except Exception:
            # Bug: silently drops failed jobs with no retries, no DLQ, no failure metric, and no log
            return False

    def process_all(self, jobs: list[Job]) -> dict[str, int]:
        processed = 0
        for job in jobs:
            if self.process_one(job):
                processed += 1
        return {"processed": processed, "failed": 0, "dlq_depth": len(self.dlq)}
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_queue_worker.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from queue_worker import Job, JobProcessor


class QueueWorkerBaselineTest(unittest.TestCase):
    def test_successful_jobs_are_counted(self):
        handled = []
        proc = JobProcessor(lambda job: handled.append(job.job_id))
        res = proc.process_all([
            Job("j-1", "email", "u-1", "r-1", {"to": "a@example.invalid"}, trace_id="t-1"),
            Job("j-2", "invoice", "u-2", "r-2", {"id": 2}, trace_id="t-2"),
        ])
        self.assertEqual(res["processed"], 2)
        self.assertEqual(handled, ["j-1", "j-2"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial unobservable job queue worker"
