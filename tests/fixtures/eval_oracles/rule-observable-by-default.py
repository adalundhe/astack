"""Separated offline oracle for `rule-observable-by-default`."""
from __future__ import annotations

from pathlib import Path

_FIXED_WORKER = '''from __future__ import annotations

import time
import uuid
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
    """Queue worker with bounded metrics, correlation-ID structured logs, retries, heartbeat, and DLQ."""

    def __init__(
        self,
        handler: Callable[[Job], None],
        *,
        metrics: MetricsRegistry | None = None,
        max_attempts: int = 2,
        log_sink: list[dict[str, Any]] | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._handler = handler
        self.metrics = metrics if metrics is not None else MetricsRegistry()
        self.max_attempts = max_attempts
        self.log_sink: list[dict[str, Any]] = log_sink if log_sink is not None else []
        self.dlq: list[DeadLetterRecord] = []
        self.last_success_ts: float | None = None

    def process_one(self, job: Job) -> bool:
        trace_id = job.trace_id or f"gen-{uuid.uuid4().hex[:12]}"
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                self._handler(job)
                now = time.time()
                self.last_success_ts = now
                self.metrics.inc(
                    "jobs_processed_total",
                    labels={"job_type": job.job_type, "outcome": "success"},
                )
                self.metrics.set_gauge("worker_last_success_timestamp", now)
                self.metrics.set_gauge("dlq_depth", float(len(self.dlq)))
                self.log_sink.append({
                    "event": "job_processed",
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "trace_id": trace_id,
                    "outcome": "success",
                    "attempts": attempt,
                })
                return True
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_attempts:
                    self.metrics.inc(
                        "jobs_retried_total",
                        labels={"job_type": job.job_type, "error_type": type(exc).__name__},
                    )

        assert last_exc is not None
        error_type = type(last_exc).__name__
        self.dlq.append(
            DeadLetterRecord(
                job=job,
                error_type=error_type,
                error_message=str(last_exc),
                trace_id=trace_id,
                attempts=self.max_attempts,
            )
        )
        self.metrics.inc(
            "jobs_failed_total",
            labels={"job_type": job.job_type, "outcome": "dlq", "error_type": error_type},
        )
        self.metrics.set_gauge("dlq_depth", float(len(self.dlq)))
        self.log_sink.append({
            "event": "job_dead_lettered",
            "job_id": job.job_id,
            "job_type": job.job_type,
            "trace_id": trace_id,
            "outcome": "dlq",
            "error_type": error_type,
            "attempts": self.max_attempts,
        })
        return False

    def process_all(self, jobs: list[Job]) -> dict[str, int]:
        processed = 0
        failed = 0
        for job in jobs:
            if self.process_one(job):
                processed += 1
            else:
                failed += 1
        return {"processed": processed, "failed": failed, "dlq_depth": len(self.dlq)}
'''

_FIXED_TESTS = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from queue_worker import Job, JobProcessor, MetricsRegistry


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

    def test_bounded_metric_cardinality_under_many_users(self):
        metrics = MetricsRegistry()
        proc = JobProcessor(lambda job: None, metrics=metrics)
        jobs = [
            Job(f"job-{i}", "email" if i % 2 == 0 else "invoice", f"user-{i}", f"req-{i}", trace_id=f"tr-{i}")
            for i in range(100)
        ]
        res = proc.process_all(jobs)
        self.assertEqual(res, {"processed": 100, "failed": 0, "dlq_depth": 0})
        self.assertLessEqual(metrics.series_count(), 10)
        self.assertIsNotNone(proc.last_success_ts)
        snap = metrics.snapshot()
        for (_, label_items) in list(snap["counters"]) + list(snap["gauges"]):
            keys = {k for k, _ in label_items}
            self.assertFalse(keys & {"user_id", "request_id", "job_id", "trace_id"})

    def test_retries_dlq_and_trace_id_propagation(self):
        attempts: dict[str, int] = {}

        def handler(job: Job) -> None:
            attempts[job.job_id] = attempts.get(job.job_id, 0) + 1
            if job.job_id == "j-perm":
                raise ValueError("bad format")
            if job.job_id == "j-flaky" and attempts[job.job_id] == 1:
                raise RuntimeError("temporary")

        logs: list[dict] = []
        metrics = MetricsRegistry()
        proc = JobProcessor(handler, metrics=metrics, max_attempts=2, log_sink=logs)
        res = proc.process_all([
            Job("j-flaky", "email", "u-1", "r-1", trace_id="trace-flaky"),
            Job("j-perm", "invoice", "u-2", "r-2", trace_id="trace-perm"),
            Job("j-notrace", "email", "u-3", "r-3", trace_id=None),
        ])
        self.assertEqual(res, {"processed": 2, "failed": 1, "dlq_depth": 1})
        self.assertEqual(len(proc.dlq), 1)
        self.assertEqual(proc.dlq[0].job.job_id, "j-perm")
        self.assertEqual(proc.dlq[0].trace_id, "trace-perm")
        self.assertEqual(proc.dlq[0].error_type, "ValueError")
        self.assertEqual(proc.dlq[0].attempts, 2)
        self.assertEqual(len(logs), 3)
        self.assertTrue(all(rec.get("trace_id") for rec in logs))
        self.assertEqual(logs[1]["trace_id"], "trace-perm")


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "queue_worker.py").write_text(_FIXED_WORKER, encoding="utf-8")
    (repo / "tests" / "test_queue_worker.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Updated src/queue_worker.py to emit bounded-cardinality metric labels, propagate trace_id "
            "across all structured log entries, track last_success_ts and dlq_depth gauges, retry transient "
            "failures up to max_attempts, and route unrecoverable failures into self.dlq with unit tests."
        ),
    }
