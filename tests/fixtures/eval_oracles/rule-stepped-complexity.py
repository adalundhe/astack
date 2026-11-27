"""Separated offline oracle for `rule-stepped-complexity`."""
from __future__ import annotations

from pathlib import Path

FIXED_CLIENT = r'''"""HTTP fetch client with progressive complexity tiers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping

from backend import send_request

DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retry_statuses: tuple[int, ...] = (502, 503, 504)


TransportFn = Callable[[str, dict[str, str], float], Response]


def default_transport(url: str, headers: dict[str, str], timeout: float) -> Response:
    status, body, resp_headers = send_request(url, headers, timeout)
    return Response(status=status, body=body, headers=resp_headers)


def fetch(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    headers: Mapping[str, str] | None = None,
    retry: RetryPolicy | None = None,
    transport: TransportFn | None = None,
) -> Response:
    """Fetch a URL across progressive tiers:
    - Tier 0: fetch(url)
    - Tier 1: fetch(url, timeout=..., headers={...})
    - Tier 2: fetch(url, ..., retry=RetryPolicy(...), transport=custom_fn)
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    policy = retry or RetryPolicy()
    if policy.max_attempts < 1:
        raise ValueError("retry.max_attempts must be >= 1")

    send = transport or default_transport
    req_headers = dict(headers) if headers else {}
    last_response: Response | None = None
    for _ in range(policy.max_attempts):
        last_response = send(url, dict(req_headers), timeout)
        if last_response.status not in policy.retry_statuses:
            return last_response
    assert last_response is not None
    return last_response
'''

FIXED_TESTS = r'''import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from http_client import Response, RetryPolicy, fetch


class HttpClientTieredApiTest(unittest.TestCase):
    def test_tier0_fetch_requires_only_url(self):
        result = fetch("https://api.acme.invalid/health")
        self.assertEqual((result.status, result.body), (200, b"ok"))

    def test_tier1_optional_timeout_and_plain_headers(self):
        result = fetch("https://api.acme.invalid/echo", timeout=2.5, headers={"X-Auth": "tok-123"})
        echo = json.loads(result.body.decode("utf-8"))
        self.assertEqual(result.status, 200)
        self.assertEqual(echo["headers"], {"X-Auth": "tok-123"})
        self.assertEqual(echo["timeout"], 2.5)

    def test_tier2_custom_transport_and_retry_policy_compose(self):
        attempts: list[tuple[str, dict[str, str], float]] = []

        def stub_transport(url: str, headers: dict[str, str], timeout: float) -> Response:
            attempts.append((url, headers, timeout))
            if len(attempts) < 3:
                return Response(status=503, body=b"retry", headers={})
            return Response(status=200, body=b"done", headers={})

        result = fetch(
            "https://api.acme.invalid/jobs",
            timeout=1.5,
            headers={"X-Trace": "t1"},
            retry=RetryPolicy(max_attempts=3),
            transport=stub_transport)
        self.assertEqual((result.status, result.body), (200, b"done"))
        self.assertEqual(len(attempts), 3)
        self.assertEqual(attempts[0][1], {"X-Trace": "t1"})
        self.assertEqual(attempts[0][2], 1.5)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    """Simplify fetch() into three progressive tiers and update unit tests."""
    repo = ws / "repo"
    (repo / "src" / "http_client.py").write_text(FIXED_CLIENT, encoding="utf-8")
    (repo / "tests" / "test_http_client.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Redesigned fetch() in src/http_client.py into three progressive tiers: "
            "Tier 0 fetch(url) with sensible defaults, Tier 1 optional timeout and plain dict headers, "
            "and Tier 2 optional RetryPolicy and custom transport callable. Updated tests/test_http_client.py "
            "to cover all three tiers."
        ),
    }
