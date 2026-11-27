#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Batch Worker

Groups `bytes` payloads into batches and delivers them to an upstream sink in `src/batch_worker.py`.

## Public Contract

### `BatchWorker(send_fn, *, max_batch_bytes: int, max_retries: int, target_batch_seconds: float | None = None, sleep_fn=time.sleep, clock_fn=time.monotonic)`
- Must remove hardcoded behavioral constants (`MAX_BATCH = 47`, `SLEEP_SEC = 3.7`, `CUTOFF = 1234`).
- Validates explicit caller configuration:
  - `max_batch_bytes`: integer strictly greater than `0` (raises `ValueError` otherwise).
  - `max_retries`: integer `>= 0` (raises `ValueError` otherwise).
  - `target_batch_seconds`: `None` or float strictly greater than `0` (raises `ValueError` otherwise).
- `send_fn(batch: list[bytes]) -> tuple[bool, float | None]`:
  - Returns `(True, None)` on success.
  - Returns `(False, retry_after_seconds)` on retryable failure.

### `process(items: list[bytes]) -> int`
- Validates each item is `bytes` and `len(item) <= max_batch_bytes` (raises `ValueError` on an oversized single item).
- Delivers **all** items without stopping at any hardcoded byte/item cutoff.
- Bounds each batch by total payload bytes (`sum(len(x) for x in batch) <= effective_batch_bytes <= max_batch_bytes`), never by an arbitrary item count.
- On retryable failure, retries up to `max_retries` times using the upstream `retry_after_seconds` passed to `sleep_fn` (when `retry_after_seconds` is positive). Raises `RuntimeError` if retries are exhausted.
- When `target_batch_seconds` is set, measures each successful send duration using `clock_fn` and adapts `effective_batch_bytes` proportionally (`int(sent_bytes * target_batch_seconds / elapsed)`) clamped to `[1, max_batch_bytes]` (always allowing at least a single valid item up to `max_batch_bytes`).
- Returns total number of items delivered.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/batch_worker.py <<'EOF'
from __future__ import annotations

import time
from typing import Callable

MAX_BATCH = 47
SLEEP_SEC = 3.7
CUTOFF = 1234


class BatchWorker:
    """Delivers payload batches using arbitrary hardcoded limits."""

    def __init__(
        self,
        send_fn: Callable[[list[bytes]], tuple[bool, float | None]],
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._send_fn = send_fn
        self._sleep_fn = sleep_fn

    def process(self, items: list[bytes]) -> int:
        delivered = 0
        total_bytes = 0
        batch: list[bytes] = []

        for item in items:
            if total_bytes + len(item) > CUTOFF:
                break
            batch.append(item)
            total_bytes += len(item)
            if len(batch) >= MAX_BATCH:
                self._flush(batch)
                delivered += len(batch)
                batch = []

        if batch:
            self._flush(batch)
            delivered += len(batch)
        return delivered

    def _flush(self, batch: list[bytes]) -> None:
        for _ in range(3):
            ok, _retry_after = self._send_fn(batch)
            if ok:
                return
            self._sleep_fn(SLEEP_SEC)
        raise RuntimeError("delivery failed")
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_batch_worker.py <<'EOF'
import unittest

from src.batch_worker import BatchWorker


class BatchWorkerBasicTest(unittest.TestCase):
    def test_delivers_small_items(self):
        sent: list[list[bytes]] = []

        def sink(batch: list[bytes]) -> tuple[bool, float | None]:
            sent.append(list(batch))
            return True, None

        worker = BatchWorker(sink)
        count = worker.process([b"abc", b"def", b"ghi"])
        self.assertEqual(count, 3)
        self.assertEqual([item for b in sent for item in b], [b"abc", b"def", b"ghi"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
