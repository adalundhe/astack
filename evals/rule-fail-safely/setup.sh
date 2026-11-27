#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Upstream Gateway

Provides `UpstreamClient` and `HealthService` in `src/gateway.py`.

## Public API & Requirements

### `UpstreamError(RuntimeError)`
Raised when an upstream request cannot be completed.

### `UpstreamClient`
```python
UpstreamClient(
    transport,
    *,
    timeout_s: float = 1.0,
    max_retries: int = 3,
    base_backoff_s: float = 0.05,
    max_backoff_s: float = 1.0,
    retry_budget: int = 5,
    sleep_fn=time.sleep,
    rng=None,
)
```
- `transport(method: str, path: str, timeout: float | None) -> tuple[int, dict]`
- `fetch(path: str) -> dict`:
  - Sends idempotent `GET` with an explicit finite positive `timeout` (`timeout_s`).
  - Retries transient failures (`TimeoutError`, `ConnectionError`, HTTP 500/502/503/504) up to `max_retries` extra attempts per call, using exponential backoff capped at `max_backoff_s` with full jitter (`rng` or `random`), sleeping via `sleep_fn`.
  - Enforces a shared `retry_budget` across calls so sustained outages cannot trigger unbounded retry storms.
  - Raises `UpstreamError` when retries or budget are exhausted, or on non-retryable 4xx responses.
- `submit(path: str, payload: dict) -> dict`:
  - Sends non-idempotent `POST` with an explicit finite positive `timeout` (`timeout_s`).
  - Never retries on failure; raises `UpstreamError` immediately.

### `HealthService`
```python
HealthService(db_ping)
```
- `db_ping() -> bool` checks downstream database connectivity.
- `liveness() -> dict`:
  - Checks only in-process liveness; must NEVER invoke `db_ping`.
  - Returns `{"status": "ok"}`.
- `readiness(timeout_s: float = 0.5) -> dict`:
  - Runs `db_ping` within `timeout_s`.
  - Returns `{"status": "ready"}` when `db_ping()` returns `True` within the deadline.
  - Returns `{"status": "not_ready", "reason": "<reason>"}` when `db_ping()` returns `False`, raises, or exceeds `timeout_s`.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/gateway.py <<'EOF'
from __future__ import annotations

import random
import time
from typing import Any, Callable


class UpstreamError(RuntimeError):
    """Raised when an upstream call fails."""


class UpstreamClient:
    """HTTP/RPC client wrapper for an upstream service."""

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
        self._transport = transport
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self.retry_budget = retry_budget
        self._sleep = sleep_fn
        self._rng = rng or random.Random()

    def fetch(self, path: str) -> dict[str, Any]:
        while True:
            try:
                status, body = self._transport("GET", path, None)
            except (TimeoutError, ConnectionError):
                continue
            if 200 <= status < 300:
                return body
            if status >= 500:
                continue
            raise UpstreamError(f"GET {path} failed with status {status}")

    def submit(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        while True:
            try:
                status, body = self._transport("POST", path, None)
            except (TimeoutError, ConnectionError):
                continue
            if 200 <= status < 300:
                return body
            if status >= 500:
                continue
            raise UpstreamError(f"POST {path} failed with status {status}")


class HealthService:
    """Service liveness and readiness probe handlers."""

    def __init__(self, db_ping: Callable[[], bool]) -> None:
        self._db_ping = db_ping

    def liveness(self) -> dict[str, str]:
        if not self._db_ping():
            return {"status": "unhealthy"}
        return {"status": "ok"}

    def readiness(self, timeout_s: float = 0.5) -> dict[str, str]:
        if self._db_ping():
            return {"status": "ready"}
        return {"status": "not_ready", "reason": "db_unavailable"}
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_gateway.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gateway import HealthService, UpstreamClient


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


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial upstream gateway scaffold"
