"""Separated offline oracle for `rule-no-shared-writes`."""
from __future__ import annotations

from pathlib import Path

_FIXED_AGGREGATOR = '''from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetricEvent:
    service: str
    status: str
    latency_ms: int


def _aggregate_events(events: list[MetricEvent]) -> dict[str, dict[str, int]]:
    local_totals: dict[str, dict[str, int]] = {}
    for ev in events:
        bucket = local_totals.get(ev.service)
        if bucket is None:
            bucket = {"count": 0, "errors": 0, "total_latency_ms": 0}
            local_totals[ev.service] = bucket
        bucket["count"] += 1
        if ev.status != "ok":
            bucket["errors"] += 1
        bucket["total_latency_ms"] += ev.latency_ms
    return local_totals


class MetricsAggregator:
    """Lock-free aggregator isolating each worker into its own partition file and merging on read."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _write_worker_partition(self, partition_id: str, events: list[MetricEvent]) -> None:
        local_totals = _aggregate_events(events)
        tmp_path = self.output_dir / f".worker-{partition_id}.tmp"
        final_path = self.output_dir / f"worker-{partition_id}.json"
        tmp_path.write_text(json.dumps(local_totals), encoding="utf-8")
        os.replace(tmp_path, final_path)

    def process_batches(self, batches: list[list[MetricEvent]]) -> dict[str, dict[str, int]]:
        run_id = uuid.uuid4().hex
        threads = [
            threading.Thread(
                target=self._write_worker_partition,
                args=(f"{run_id}-{idx:04d}", batch),
            )
            for idx, batch in enumerate(batches)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return self.read_summary()

    def read_summary(self) -> dict[str, dict[str, int]]:
        merged: dict[str, dict[str, int]] = {}
        for part_file in sorted(self.output_dir.glob("worker-*.json")):
            data = json.loads(part_file.read_text(encoding="utf-8"))
            for service, metrics in data.items():
                bucket = merged.get(service)
                if bucket is None:
                    bucket = {"count": 0, "errors": 0, "total_latency_ms": 0}
                    merged[service] = bucket
                bucket["count"] += int(metrics["count"])
                bucket["errors"] += int(metrics["errors"])
                bucket["total_latency_ms"] += int(metrics["total_latency_ms"])
        return dict(sorted(merged.items()))
'''

_FIXED_TESTS = '''import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aggregator import MetricEvent, MetricsAggregator


class AggregatorBaselineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="agg-baseline-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_single_batch_aggregates_service_metrics(self):
        agg = MetricsAggregator(self.tmp)
        summary = agg.process_batches([[
            MetricEvent("auth", "ok", 10),
            MetricEvent("auth", "error", 25),
            MetricEvent("billing", "ok", 40),
        ]])
        self.assertEqual(
            summary,
            {
                "auth": {"count": 2, "errors": 1, "total_latency_ms": 35},
                "billing": {"count": 1, "errors": 0, "total_latency_ms": 40},
            },
        )

    def test_concurrent_batches_lose_zero_events_and_merge_on_read(self):
        agg = MetricsAggregator(self.tmp)
        batches = [
            [
                MetricEvent("payments", "ok" if i % 4 else "error", 10 + i)
                for i in range(30)
            ]
            for _ in range(10)
        ]
        summary = agg.process_batches(batches)
        expected_latency = 10 * sum(10 + i for i in range(30))
        expected_errors = 10 * sum(1 for i in range(30) if i % 4 == 0)
        self.assertEqual(
            summary,
            {
                "payments": {
                    "count": 300,
                    "errors": expected_errors,
                    "total_latency_ms": expected_latency,
                }
            },
        )
        # Re-read from a fresh instance
        fresh = MetricsAggregator(self.tmp)
        self.assertEqual(fresh.read_summary(), summary)

        # Second invocation accumulates without clobbering
        second = agg.process_batches([[MetricEvent("payments", "ok", 5)]])
        self.assertEqual(second["payments"]["count"], 301)
        self.assertEqual(second["payments"]["total_latency_ms"], expected_latency + 5)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "aggregator.py").write_text(_FIXED_AGGREGATOR, encoding="utf-8")
    (repo / "tests" / "test_aggregator.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Replaced shared dict and shared summary.json writes in src/aggregator.py with lock-free "
            "per-worker local aggregation and uniquely named atomic worker partition files merged in "
            "read_summary(), and added concurrent multi-batch stress tests."
        ),
    }
