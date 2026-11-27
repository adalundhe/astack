#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Concurrent Metrics Aggregator

Provides `MetricEvent` and `MetricsAggregator` in `src/aggregator.py`.

## Public API & Contract
- `MetricEvent(service: str, status: str, latency_ms: int)`:
  - `status == "ok"` is a success; any other `status` counts as an error.
- `MetricsAggregator(output_dir: Path)`:
  - `process_batches(batches: list[list[MetricEvent]]) -> dict[str, dict[str, int]]`:
    - Processes batches concurrently across worker threads (one worker per batch).
    - Each worker writes its own isolated output file under `output_dir` (no shared mutable dict across threads, no shared `summary.json` overwritten by all workers, and no locks).
    - Multiple calls to `process_batches` on the same `output_dir` must preserve previous worker outputs and accumulate totals.
    - Returns merged totals: `{service: {"count": int, "errors": int, "total_latency_ms": int}}`.
  - `read_summary() -> dict[str, dict[str, int]]`:
    - Reads all isolated worker output files in `output_dir` and merges them into `{service: {"count": int, "errors": int, "total_latency_ms": int}}`.
    - Must produce exact totals even when called from a fresh `MetricsAggregator(output_dir)` instance.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/aggregator.py <<'EOF'
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MetricEvent:
    service: str
    status: str
    latency_ms: int


class MetricsAggregator:
    """Multi-threaded aggregator with unsafe shared dict and shared file writes."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._summary_file = self.output_dir / "summary.json"
        self._totals: dict[str, dict[str, int]] = {}

    def _run_worker(self, events: list[MetricEvent]) -> None:
        for ev in events:
            entry = self._totals.setdefault(
                ev.service, {"count": 0, "errors": 0, "total_latency_ms": 0}
            )
            old_count = entry["count"]
            old_errors = entry["errors"]
            old_latency = entry["total_latency_ms"]
            time.sleep(0.0005)
            entry["count"] = old_count + 1
            entry["errors"] = old_errors + (0 if ev.status == "ok" else 1)
            entry["total_latency_ms"] = old_latency + ev.latency_ms

        existing: dict[str, dict[str, int]] = {}
        if self._summary_file.is_file():
            try:
                existing = json.loads(self._summary_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
        time.sleep(0.001)
        for ev in events:
            bucket = existing.setdefault(
                ev.service, {"count": 0, "errors": 0, "total_latency_ms": 0}
            )
            bucket["count"] += 1
            bucket["errors"] += 0 if ev.status == "ok" else 1
            bucket["total_latency_ms"] += ev.latency_ms
        self._summary_file.write_text(json.dumps(existing), encoding="utf-8")

    def process_batches(self, batches: list[list[MetricEvent]]) -> dict[str, dict[str, int]]:
        threads = [threading.Thread(target=self._run_worker, args=(batch,)) for batch in batches]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return self.read_summary()

    def read_summary(self) -> dict[str, dict[str, int]]:
        if not self._summary_file.is_file():
            return {}
        return json.loads(self._summary_file.read_text(encoding="utf-8"))
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_aggregator.py <<'EOF'
import shutil
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


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial shared-write metrics aggregator"
