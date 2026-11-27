"""Separated offline oracle for `rule-fail-safely`."""
from __future__ import annotations

from pathlib import Path

_FIXED_GATEWAY = '''from __future__ import annotations

import concurrent.futures
import random
import time
from typing import Any, Callable

_RETRYABLE_STATUSES = frozenset({500, 502, 503, 504})


class UpstreamError(RuntimeError):
    """Raised when an upstream call fails."""


class UpstreamClient:
    """HTTP/RPC client with bounded timeouts, jittered backoff, and a retry budget."""

    def __init__(
        self,
        transport: Callable[[str, str, float | None], tuple[int, dict[str, Any]]],
        *,
        timeout_s: float = 1.0,
        max_retries: int = 3,
        base_backoff_s: float = 0.05,
        max_backoff_s: float = 1.0,
        retry_budget: int = 5,
        sleep_fn: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if base_backoff_s < 0 or max_backoff_s < 0:
            raise ValueError("backoff bounds must be >= 0")
        if retry_budget < 0:
            raise ValueError("retry_budget must be >= 0")
        self._transport = transport
        self.timeout_s = float(timeout_s)
        self.max_retries = int(max_retries)
        self.base_backoff_s = float(base_backoff_s)
        self.max_backoff_s = float(max_backoff_s)
        self.retry_budget = int(retry_budget)
        self._retries_used = 0
        self._sleep = sleep_fn
        self._rng = rng if rng is not None else random.Random()

    def _backoff_delay(self, attempt: int) -> float:
        ceiling = min(self.max_backoff_s, self.base_backoff_s * (2 ** attempt))
        if ceiling <= 0:
            return 0.0
        return self._rng.uniform(0.0, ceiling)

    def fetch(self, path: str) -> dict[str, Any]:
        last_error = "unknown failure"
        for attempt in range(self.max_retries + 1):
            retryable = False
            try:
                status, body = self._transport("GET", path, self.timeout_s)
                if 200 <= status < 300:
                    return body
                if status in _RETRYABLE_STATUSES:
                    retryable = True
                    last_error = f"HTTP {status}"
                else:
                    raise UpstreamError(f"GET {path} failed with status {status}")
            except (TimeoutError, ConnectionError) as exc:
                retryable = True
                last_error = str(exc) or type(exc).__name__

            if not retryable or attempt >= self.max_retries or self._retries_used >= self.retry_budget:
                break
            self._retries_used += 1
            self._sleep(self._backoff_delay(attempt))

        raise UpstreamError(f"GET {path} failed after retries: {last_error}")

    def submit(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            status, body = self._transport("POST", path, self.timeout_s)
        except (TimeoutError, ConnectionError) as exc:
            raise UpstreamError(f"POST {path} failed: {exc}") from exc
        if 200 <= status < 300:
            return body
        raise UpstreamError(f"POST {path} failed with status {status}")


class HealthService:
    """Service probes with in-process liveness and deadline-bounded readiness."""

    def __init__(self, db_ping: Callable[[], bool]) -> None:
        self._db_ping = db_ping

    def liveness(self) -> dict[str, str]:
        return {"status": "ok"}

    def readiness(self, timeout_s: float = 0.5) -> dict[str, str]:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._db_ping)
        try:
            healthy = bool(future.result(timeout=timeout_s))
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            return {"status": "not_ready", "reason": "db_timeout"}
        except Exception as exc:
            executor.shutdown(wait=False, cancel_futures=True)
            return {"status": "not_ready", "reason": f"db_error: {type(exc).__name__}"}
        executor.shutdown(wait=False)
        if healthy:
            return {"status": "ready"}
        return {"status": "not_ready", "reason": "db_unavailable"}
'''

_FIXED_TESTS = '''import random
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gateway import HealthService, UpstreamClient, UpstreamError


class GatewayBaselineTest(unittest.TestCase):
    def test_fetch_returns_body_on_200(self):
        client = UpstreamClient(lambda method, path, timeout: (200, {"ok": True, "path": path}))
        self.assertEqual(client.fetch("/items"), {"ok": True, "path": "/items"})

    def test_submit_returns_body_on_201(self):
        client = UpstreamClient(lambda method, path, timeout: (201, {"created": True}))
        self.assertEqual(client.submit("/orders", {"qty": 1}), {"created": True})

    def test_readiness_healthy_db(self):
        health = HealthService(lambda: True)
        self.assertEqual(health.readiness(), {"status": "ready"})

    def test_fetch_passes_timeout_and_bounds_jittered_retries(self):
        timeouts: list[float | None] = []
        sleeps: list[float] = []

        def flaky(method, path, timeout):
            timeouts.append(timeout)
            if len(timeouts) > 10:
                raise AssertionError("unbounded retry loop")
            return (503, {"error": "busy"})

        client = UpstreamClient(
            flaky,
            timeout_s=0.4,
            max_retries=3,
            base_backoff_s=0.05,
            max_backoff_s=0.3,
            retry_budget=6,
            sleep_fn=sleeps.append,
            rng=random.Random(12),
        )
        with self.assertRaises(UpstreamError):
            client.fetch("/flaky")
        self.assertEqual(timeouts, [0.4, 0.4, 0.4, 0.4])
        self.assertEqual(len(sleeps), 3)
        self.assertTrue(all(0.0 <= d <= 0.3 for d in sleeps))

    def test_retry_budget_caps_outage_burst(self):
        calls = 0

        def blackhole(method, path, timeout):
            nonlocal calls
            calls += 1
            if calls > 25:
                raise AssertionError("retry budget bypassed")
            raise TimeoutError("timed out")

        client = UpstreamClient(
            blackhole,
            timeout_s=0.2,
            max_retries=3,
            retry_budget=3,
            sleep_fn=lambda _: None,
            rng=random.Random(1),
        )
        for idx in range(5):
            with self.assertRaises(UpstreamError):
                client.fetch(f"/x/{idx}")
        self.assertEqual(calls, 8)

    def test_submit_never_retries_post(self):
        calls = 0

        def fail_post(method, path, timeout):
            nonlocal calls
            calls += 1
            if calls > 3:
                raise AssertionError("POST retried")
            return (502, {})

        client = UpstreamClient(fail_post, timeout_s=0.5, max_retries=3, sleep_fn=lambda _: None)
        with self.assertRaises(UpstreamError):
            client.submit("/orders", {"id": 1})
        self.assertEqual(calls, 1)

    def test_liveness_decoupled_and_readiness_bounds_db_stall(self):
        pings = 0

        def slow_db():
            nonlocal pings
            pings += 1
            time.sleep(0.6)
            return True

        health = HealthService(slow_db)
        self.assertEqual(health.liveness(), {"status": "ok"})
        self.assertEqual(pings, 0)

        t0 = time.monotonic()
        res = health.readiness(timeout_s=0.05)
        elapsed = time.monotonic() - t0
        self.assertEqual(res["status"], "not_ready")
        self.assertLess(elapsed, 0.4)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "gateway.py").write_text(_FIXED_GATEWAY, encoding="utf-8")
    (repo / "tests" / "test_gateway.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Hardened src/gateway.py with explicit finite timeouts, bounded jittered exponential backoff "
            "and a shared retry budget for idempotent GET requests, single-attempt non-idempotent POST submission, "
            "in-process liveness decoupled from db_ping, and deadline-bounded readiness checks with fault-injection tests."
        ),
    }
