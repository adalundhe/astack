#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/backend.py <<'EOF'
"""In-process simulated HTTP backend for offline deterministic client calls."""
from __future__ import annotations

import json


def send_request(url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes, dict[str, str]]:
    """Simulate an HTTP GET against `url` without opening network sockets."""
    if url.endswith("/health"):
        return 200, b"ok", {"content-type": "text/plain"}
    payload = json.dumps(
        {"url": url, "headers": dict(sorted(headers.items())), "timeout": timeout},
        sort_keys=True,
    ).encode("utf-8")
    return 200, payload, {"content-type": "application/json"}
EOF

cat > repo/src/http_client.py <<'EOF'
"""HTTP fetch client with high-ceremony mandatory configuration objects."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from backend import send_request


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TransportConfig:
    transport: Callable[[str, dict[str, str], float], Response] | None = None


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retry_statuses: tuple[int, ...] = (502, 503, 504)


@dataclass(frozen=True)
class HeaderBundle:
    values: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TimeoutSpec:
    seconds: float = 10.0


@dataclass(frozen=True)
class TLSOptions:
    verify: bool = True


@dataclass(frozen=True)
class MetricsSink:
    namespace: str = "http"


def default_transport(url: str, headers: dict[str, str], timeout: float) -> Response:
    status, body, resp_headers = send_request(url, headers, timeout)
    return Response(status=status, body=body, headers=resp_headers)


def fetch(
    url: str,
    transport_config: TransportConfig,
    retry_policy: RetryPolicy,
    header_bundle: HeaderBundle,
    timeout_spec: TimeoutSpec,
    tls_options: TLSOptions,
    metrics_sink: MetricsSink,
) -> Response:
    """Fetch a URL. Currently forces every caller to construct six mandatory objects."""
    _ = (tls_options, metrics_sink)
    send = transport_config.transport or default_transport
    attempts = max(1, retry_policy.max_attempts)
    last_response: Response | None = None
    for _attempt in range(attempts):
        last_response = send(url, dict(header_bundle.values), timeout_spec.seconds)
        if last_response.status not in retry_policy.retry_statuses:
            return last_response
    assert last_response is not None
    return last_response
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_http_client.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from http_client import (
    HeaderBundle,
    MetricsSink,
    RetryPolicy,
    TLSOptions,
    TimeoutSpec,
    TransportConfig,
    fetch,
)


class HttpClientBaselineTest(unittest.TestCase):
    def test_fetch_with_full_ceremony(self):
        resp = fetch(
            "https://api.acme.invalid/health",
            TransportConfig(),
            RetryPolicy(),
            HeaderBundle(),
            TimeoutSpec(),
            TLSOptions(),
            MetricsSink(),
        )
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.body, b"ok")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial high-ceremony http client"
git -C repo rev-parse HEAD > program/base_sha.txt
