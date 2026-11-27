"""Separated offline oracle for `rule-event-driven`."""
from __future__ import annotations

from pathlib import Path

FIXED_SRC = '''from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import threading
import time
from typing import Any, Callable


class JobRunner:
    """Runs background callables and wakes waiters directly via Future completion notifications."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._lock = threading.Lock()
        self._futures: dict[str, Future[Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, job_id: str, fn: Callable[[], Any]) -> str:
        with self._lock:
            if job_id in self._futures:
                raise ValueError(f"duplicate job_id: {job_id}")
            future = self._executor.submit(fn)
            self._futures[job_id] = future
        return job_id

    def _get_future(self, job_id: str) -> Future[Any]:
        with self._lock:
            if job_id not in self._futures:
                raise KeyError(f"unknown job_id: {job_id}")
            return self._futures[job_id]

    def wait_for(self, job_id: str, timeout: float | None = None) -> Any:
        future = self._get_future(job_id)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError as exc:
            raise TimeoutError(f"timed out waiting for job {job_id}") from exc

    def wait_all(self, job_ids: list[str], timeout: float | None = None) -> dict[str, Any]:
        futures = [(jid, self._get_future(jid)) for jid in job_ids]
        deadline = None if timeout is None else time.monotonic() + timeout
        results: dict[str, Any] = {}
        for job_id, future in futures:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            try:
                results[job_id] = future.result(timeout=remaining)
            except FutureTimeoutError as exc:
                raise TimeoutError(f"timed out waiting for job {job_id}") from exc
        return results

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait)
'''

FIXED_TESTS = '''import threading
import time
import unittest
from unittest import mock

from src.job_runner import JobRunner


class JobRunnerBasicTest(unittest.TestCase):
    def test_submit_and_wait_for_returns_result(self):
        runner = JobRunner()
        try:
            runner.submit("job-1", lambda: 21 * 2)
            self.assertEqual(runner.wait_for("job-1", timeout=2.0), 42)
        finally:
            runner.shutdown()

    def test_wakes_on_completion_event_without_sleep_polling(self):
        runner = JobRunner()
        gate = threading.Event()
        try:
            with mock.patch.object(time, "sleep", side_effect=AssertionError("time.sleep must not be called")):
                runner.submit("gated", lambda: (gate.wait(5.0), "done")[1])
                result_box: list[str] = []

                def waiter() -> None:
                    result_box.append(runner.wait_for("gated", timeout=5.0))

                wt = threading.Thread(target=waiter)
                wt.start()
                gate.set()
                wt.join(timeout=5.0)
                self.assertFalse(wt.is_alive())
                self.assertEqual(result_box, ["done"])
        finally:
            runner.shutdown()

    def test_propagates_failure_timeout_and_unknown_job_without_sleep(self):
        runner = JobRunner()
        blocker = threading.Event()
        try:
            with mock.patch.object(time, "sleep", side_effect=AssertionError("time.sleep must not be called")):
                with self.assertRaises(KeyError):
                    runner.wait_for("unknown", timeout=1.0)

                def fail_job() -> None:
                    raise ValueError("worker failure")

                runner.submit("bad", fail_job)
                with self.assertRaises(ValueError):
                    runner.wait_for("bad", timeout=2.0)

                runner.submit("slow", lambda: blocker.wait(5.0))
                with self.assertRaises(TimeoutError):
                    runner.wait_for("slow", timeout=0.05)
                blocker.set()
                self.assertTrue(runner.wait_for("slow", timeout=2.0))
        finally:
            blocker.set()
            runner.shutdown()

    def test_wait_all_collects_multiple_jobs_and_rejects_duplicates(self):
        runner = JobRunner()
        g1, g2 = threading.Event(), threading.Event()
        try:
            with mock.patch.object(time, "sleep", side_effect=AssertionError("time.sleep must not be called")):
                runner.submit("j1", lambda: (g1.wait(5.0), "one")[1])
                runner.submit("j2", lambda: (g2.wait(5.0), "two")[1])
                with self.assertRaises(ValueError):
                    runner.submit("j1", lambda: "dup")
                g1.set()
                g2.set()
                self.assertEqual(runner.wait_all(["j1", "j2"], timeout=2.0), {"j1": "one", "j2": "two"})
                with self.assertRaises(KeyError):
                    runner.wait_all(["j1", "missing"], timeout=1.0)
        finally:
            g1.set()
            g2.set()
            runner.shutdown()


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "job_runner.py").write_text(FIXED_SRC, encoding="utf-8")
    (repo / "tests" / "test_job_runner.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Replaced the time.sleep(0.2) polling loops in src/job_runner.py with "
            "ThreadPoolExecutor Futures so wait_for and wait_all wake immediately on "
            "completion or exception with bounded deadlines, raise KeyError immediately "
            "for unknown job IDs, and verified zero time.sleep calls with deterministic tests."
        ),
    }
