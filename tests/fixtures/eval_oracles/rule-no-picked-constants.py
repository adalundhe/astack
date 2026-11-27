"""Separated offline oracle for `rule-no-picked-constants`."""
from __future__ import annotations

from pathlib import Path

FIXED_SRC = '''from __future__ import annotations

import time
from typing import Callable


class BatchWorker:
    """Delivers payload batches bounded by explicit caller byte limits and runtime latency feedback."""

    def __init__(
        self,
        send_fn: Callable[[list[bytes]], tuple[bool, float | None]],
        *,
        max_batch_bytes: int,
        max_retries: int,
        target_batch_seconds: float | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(max_batch_bytes, bool) or not isinstance(max_batch_bytes, int) or max_batch_bytes <= 0:
            raise ValueError("max_batch_bytes must be a positive integer")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if target_batch_seconds is not None and (
            isinstance(target_batch_seconds, bool)
            or not isinstance(target_batch_seconds, (int, float))
            or target_batch_seconds <= 0
        ):
            raise ValueError("target_batch_seconds must be positive when provided")

        self._send_fn = send_fn
        self._max_batch_bytes = max_batch_bytes
        self._effective_batch_bytes = max_batch_bytes
        self._max_retries = max_retries
        self._target_batch_seconds = float(target_batch_seconds) if target_batch_seconds is not None else None
        self._sleep_fn = sleep_fn
        self._clock_fn = clock_fn

    def process(self, items: list[bytes]) -> int:
        for item in items:
            if not isinstance(item, bytes):
                raise ValueError("each item must be bytes")
            if len(item) > self._max_batch_bytes:
                raise ValueError(
                    f"single item size {len(item)} exceeds max_batch_bytes={self._max_batch_bytes}"
                )

        delivered = 0
        idx = 0
        total = len(items)
        while idx < total:
            budget = self._effective_batch_bytes
            batch: list[bytes] = []
            batch_bytes = 0
            while idx < total:
                item = items[idx]
                if batch and batch_bytes + len(item) > budget:
                    break
                batch.append(item)
                batch_bytes += len(item)
                idx += 1
            self._flush(batch, batch_bytes)
            delivered += len(batch)
        return delivered

    def _flush(self, batch: list[bytes], batch_bytes: int) -> None:
        attempt = 0
        while True:
            started = self._clock_fn()
            ok, retry_after = self._send_fn(batch)
            elapsed = self._clock_fn() - started
            if ok:
                self._adapt_budget(batch_bytes, elapsed)
                return
            if attempt >= self._max_retries:
                raise RuntimeError(f"delivery failed after {attempt} retry attempt(s)")
            attempt += 1
            if retry_after is not None and retry_after > 0:
                self._sleep_fn(float(retry_after))

    def _adapt_budget(self, sent_bytes: int, elapsed: float) -> None:
        if self._target_batch_seconds is None or elapsed <= 0 or sent_bytes <= 0:
            return
        scaled = int(sent_bytes * (self._target_batch_seconds / elapsed))
        self._effective_batch_bytes = max(1, min(self._max_batch_bytes, scaled))
'''

FIXED_TESTS = '''import unittest

from src.batch_worker import BatchWorker


class BatchWorkerBasicTest(unittest.TestCase):
    def test_delivers_small_items(self):
        sent: list[list[bytes]] = []

        def sink(batch: list[bytes]) -> tuple[bool, float | None]:
            sent.append(list(batch))
            return True, None

        worker = BatchWorker(sink, max_batch_bytes=512, max_retries=1)
        count = worker.process([b"abc", b"def", b"ghi"])
        self.assertEqual(count, 3)
        self.assertEqual([item for b in sent for item in b], [b"abc", b"def", b"ghi"])

    def test_packs_small_and_large_payloads_by_byte_budget(self):
        sent_small: list[list[bytes]] = []
        w_small = BatchWorker(
            lambda b: (sent_small.append(list(b)) is None, None),
            max_batch_bytes=600,
            max_retries=0,
        )
        items_small = [b"a" * 10 for _ in range(120)]
        self.assertEqual(w_small.process(items_small), 120)
        self.assertEqual([len(b) for b in sent_small], [60, 60])

        sent_large: list[list[bytes]] = []
        w_large = BatchWorker(
            lambda b: (sent_large.append(list(b)) is None, None),
            max_batch_bytes=500,
            max_retries=0,
        )
        items_large = [b"b" * 300 for _ in range(6)]
        self.assertEqual(w_large.process(items_large), 6)
        self.assertEqual([len(b) for b in sent_large], [1, 1, 1, 1, 1, 1])

    def test_delivers_volumes_exceeding_legacy_cutoff_and_rejects_oversized_item(self):
        sent: list[list[bytes]] = []
        worker = BatchWorker(
            lambda b: (sent.append(list(b)) is None, None),
            max_batch_bytes=400,
            max_retries=1,
        )
        items = [b"x" * 100 for _ in range(25)]
        self.assertEqual(worker.process(items), 25)
        self.assertEqual(sum(len(b) for b in sent), 25)

        with self.assertRaises(ValueError):
            worker.process([b"x" * 401])

    def test_honors_server_retry_after_and_max_retries(self):
        waits: list[float] = []
        outcomes = iter([(False, 0.25), (False, 1.5), (True, None)])
        worker = BatchWorker(
            lambda b: next(outcomes),
            max_batch_bytes=256,
            max_retries=2,
            sleep_fn=waits.append,
        )
        self.assertEqual(worker.process([b"msg"]), 1)
        self.assertEqual(waits, [0.25, 1.5])

        fail_waits: list[float] = []
        failing = BatchWorker(
            lambda b: (False, 0.1),
            max_batch_bytes=256,
            max_retries=1,
            sleep_fn=fail_waits.append,
        )
        with self.assertRaises(RuntimeError):
            failing.process([b"msg"])
        self.assertEqual(fail_waits, [0.1])

    def test_adapts_batch_bytes_from_measured_latency(self):
        now = [0.0]
        batches: list[list[bytes]] = []

        def slow_sink(batch: list[bytes]) -> tuple[bool, float | None]:
            batches.append(list(batch))
            now[0] += 2.0 if len(batches) == 1 else 0.5
            return True, None

        worker = BatchWorker(
            slow_sink,
            max_batch_bytes=1000,
            max_retries=1,
            target_batch_seconds=0.5,
            sleep_fn=lambda _: None,
            clock_fn=lambda: now[0],
        )
        self.assertEqual(worker.process([b"m" * 50 for _ in range(30)]), 30)
        self.assertEqual(sum(len(x) for x in batches[0]), 1000)
        self.assertEqual(sum(len(x) for x in batches[1]), 250)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "batch_worker.py").write_text(FIXED_SRC, encoding="utf-8")
    (repo / "tests" / "test_batch_worker.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Removed hardcoded MAX_BATCH, SLEEP_SEC, and CUTOFF constants from src/batch_worker.py, "
            "switched BatchWorker to explicit caller-supplied max_batch_bytes and max_retries limits "
            "with upstream Retry-After waiting and runtime latency-based batch byte adaptation, and "
            "added unit tests covering varied payload sizes, retry signals, and runtime adaptation."
        ),
    }
