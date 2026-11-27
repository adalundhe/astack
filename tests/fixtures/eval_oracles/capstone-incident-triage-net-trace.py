"""Separated offline oracle for `capstone-incident-triage-net-trace`."""
from __future__ import annotations

from pathlib import Path

_HARDENED_GATEWAY = '''"""Hardened payment gateway client for edge-api."""
from __future__ import annotations

import random
import time
from typing import Any, Callable

_SENSITIVE_HEADERS = frozenset({"authorization", "x-api-key", "proxy-authorization", "cookie"})


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with credential values replaced by [REDACTED]."""
    scrubbed: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _SENSITIVE_HEADERS:
            scrubbed[k] = "[REDACTED]"
        else:
            scrubbed[k] = v
    return scrubbed


class ListLogger:
    def __init__(self) -> None:
        self.records: list[str] = []

    def info(self, msg: str) -> None:
        self.records.append(f"INFO: {msg}")

    def warning(self, msg: str) -> None:
        self.records.append(f"WARN: {msg}")

    def error(self, msg: str) -> None:
        self.records.append(f"ERROR: {msg}")


class InMemoryMetrics:
    def __init__(self) -> None:
        self.counters: list[tuple[str, dict[str, str]]] = []

    def inc(self, name: str, labels: dict[str, str] | None = None) -> None:
        self.counters.append((name, dict(labels or {})))


class PaymentGateway:
    def __init__(
        self,
        transport: Callable[..., dict[str, Any]],
        logger: Any | None = None,
        metrics: Any | None = None,
        endpoint: str = "https://processor.pay.invalid/v1/charge",
        *,
        timeout_seconds: float = 3.0,
        max_attempts: int = 3,
        base_backoff_seconds: float = 0.1,
        max_backoff_seconds: float = 2.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._transport = transport
        self._logger = logger or ListLogger()
        self._metrics = metrics or InMemoryMetrics()
        self._endpoint = endpoint
        self._timeout_seconds = float(timeout_seconds)
        self._max_attempts = int(max_attempts)
        self._base_backoff = float(base_backoff_seconds)
        self._max_backoff = float(max_backoff_seconds)

    def send_payment(
        self,
        request_id: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        safe_headers = redact_headers(headers)
        self._logger.info(f"sending payment request_id={request_id} headers={safe_headers}")

        last_exc: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                resp = self._transport(
                    self._endpoint,
                    payload=payload,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
                status_class = f"{int(resp.get('status', 200)) // 100}xx"
                self._metrics.inc(
                    "gateway_requests_total",
                    labels={"status_class": status_class, "outcome": "success"},
                )
                return resp
            except (TimeoutError, ConnectionError) as exc:
                last_exc = exc
                self._metrics.inc(
                    "gateway_retries_total",
                    labels={"outcome": "retry", "error_type": type(exc).__name__},
                )
                self._logger.warning(
                    f"payment attempt {attempt}/{self._max_attempts} failed err={type(exc).__name__}"
                )
                if attempt < self._max_attempts:
                    cap = min(self._max_backoff, self._base_backoff * (2 ** (attempt - 1)))
                    delay = random.uniform(cap * 0.5, cap)
                    time.sleep(delay)

        self._metrics.inc(
            "gateway_requests_total",
            labels={"status_class": "5xx", "outcome": "exhausted"},
        )
        assert last_exc is not None
        raise last_exc
'''

_HARDENED_TESTS = r'''"""Behavioral tests for hardened PaymentGateway."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gateway import InMemoryMetrics, ListLogger, PaymentGateway


class HardenedGatewayTests(unittest.TestCase):
    def test_send_payment_happy_path(self) -> None:
        seen: list[object] = []

        def ok_transport(url, *, payload, headers, timeout):
            seen.append(timeout)
            return {"status": 200, "tx_id": "tx-1"}

        logger = ListLogger()
        metrics = InMemoryMetrics()
        gw = PaymentGateway(ok_transport, logger=logger, metrics=metrics)
        resp = gw.send_payment("req-1", {"amount": 500}, {"X-Trace": "t1"})
        self.assertEqual(resp["status"], 200)
        self.assertEqual(len(seen), 1)
        self.assertIsInstance(seen[0], float)
        self.assertGreater(seen[0], 0.0)

    def test_bounded_retry_budget_with_backoff_and_timeout(self) -> None:
        calls: list[object] = []

        def failing_transport(url, *, payload, headers, timeout):
            calls.append(timeout)
            raise TimeoutError("egress dropped")

        gw = PaymentGateway(failing_transport, logger=ListLogger(), metrics=InMemoryMetrics(), max_attempts=3)
        with patch("gateway.time.sleep") as mock_sleep:
            with self.assertRaises(TimeoutError):
                gw.send_payment("req-storm", {"amount": 100}, {"X-Trace": "t2"})
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(isinstance(t, float) and t > 0 for t in calls))
        self.assertEqual(mock_sleep.call_count, 2)

    def test_redacts_authorization_and_api_key_headers_in_logs(self) -> None:
        def ok_transport(url, *, payload, headers, timeout):
            return {"status": 200}

        logger = ListLogger()
        gw = PaymentGateway(ok_transport, logger=logger, metrics=InMemoryMetrics())
        synth_auth = "Bearer " + "demo_token_" + "987654321"
        synth_key = "api_key_" + "secret_val"
        gw.send_payment("req-sec", {"amount": 25}, {"Authorization": synth_auth, "X-Api-Key": synth_key})
        joined = "\n".join(logger.records)
        self.assertNotIn("demo_token_987654321", joined)
        self.assertNotIn("secret_val", joined)
        self.assertIn("[REDACTED]", joined)

    def test_metrics_exclude_high_cardinality_request_id(self) -> None:
        def ok_transport(url, *, payload, headers, timeout):
            return {"status": 200}

        metrics = InMemoryMetrics()
        gw = PaymentGateway(ok_transport, logger=ListLogger(), metrics=metrics)
        for idx in range(5):
            gw.send_payment(f"req-card-{idx}", {"amount": 10}, {})
        self.assertTrue(metrics.counters)
        for _name, labels in metrics.counters:
            self.assertNotIn("request_id", labels)


if __name__ == "__main__":
    unittest.main()
'''

_INCIDENT_REPORT = """# Incident Report — `edge-api` Payment Egress Outage (2026-11-26)

## Root Cause Summary
1. **Primary Network Failure (`subnet-pay-2` egress TCP/443 `DROP`):**
   At `2026-11-26T06:14:00Z`, firewall change `fw-change-882` modified `sg-pay-2` and `nacl-pay-2` on `subnet-pay-2`. Immediately at `06:14:04Z`, VPC flow logs switched from `ACCEPT` to `DROP` on outbound TCP/443 traffic from `subnet-pay-2` to `198.51.100.77` (`processor.pay.invalid`).
2. **Application Amplifier (`repo/src/gateway.py` retry storm):**
   `PaymentGateway.send_payment` called `transport` with `timeout=None` inside an unbounded `while True` retry loop with zero backoff or jitter (`attempt=47`, `attempt=112`), saturating worker threads. It also logged raw `Authorization` headers and attached high-cardinality `request_id` labels to metrics.

## Cleared Layers & Ruled-Out Decoy
- **DNS:** Healthy (`processor.pay.invalid` resolves to `198.51.100.77`, `NOERROR`).
- **TLS & Upstream:** Healthy (`subnet-pay-1` passes `ACCEPT` on TCP/443 with valid certificate through `2027-09-01`). `subnet-pay-2` times out before TCP SYN-ACK / ClientHello.
- **CPU Warning Decoy (`node-metrics-cpu-warn`):** Explicitly **ruled out** as unrelated. The 63% CPU warning on `batch-analytics-pool` started `2026-11-25T14:00:00Z` (16 hours prior) and stayed flat across `06:14Z`.

## Remediation
- **Network mitigation:** Roll back `fw-change-882` / restore scoped egress TCP/443 allow rule to `198.51.100.77/32` on `sg-pay-2` and `nacl-pay-2`.
- **Code hardening (`repo/src/gateway.py`):** Added finite `timeout_seconds=3.0`, bounded `max_attempts=3` with exponential backoff + jitter, header redaction (`[REDACTED]`), and low-cardinality `status_class`/`outcome` labels.
- **Persisted scrubbed diagnostics:**
  - `program/astack_home/edge-api/logging/logs/app_logs_scrubbed_2026_11_26_06_20_00.log`
  - `program/astack_home/edge-api/logging/traces/subnet_pay2_egress_2026_11_26_06_20_00.trace`
"""


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "gateway.py").write_text(_HARDENED_GATEWAY, encoding="utf-8")
    (repo / "tests" / "test_gateway.py").write_text(_HARDENED_TESTS, encoding="utf-8")
    (ws / "program" / "INCIDENT_REPORT.md").write_text(_INCIDENT_REPORT, encoding="utf-8")

    logging_root = ws / "program" / "astack_home" / "edge-api" / "logging"
    logs_dir = logging_root / "logs"
    traces_dir = logging_root / "traces"
    logs_dir.mkdir(parents=True, exist_ok=True)
    traces_dir.mkdir(parents=True, exist_ok=True)

    (logs_dir / "app_logs_scrubbed_2026_11_26_06_20_00.log").write_text(
        "2026-11-26T06:14:05Z level=INFO svc=edge-api subnet=subnet-pay-2 req=req-8801 "
        "msg=\"sending request headers={'Authorization': '[REDACTED]', 'X-Request-Id': 'req-8801'} timeout=None\"\n"
        "2026-11-26T06:14:06Z level=WARN svc=edge-api subnet=subnet-pay-2 req=req-8801 "
        "msg=\"transport timeout error, retrying immediately attempt=47\"\n"
        "2026-11-26T06:14:07Z level=WARN svc=edge-api subnet=subnet-pay-2 req=req-8801 "
        "msg=\"transport timeout error, retrying immediately attempt=112\"\n",
        encoding="utf-8",
    )
    (traces_dir / "subnet_pay2_egress_2026_11_26_06_20_00.trace").write_text(
        "2026-11-26T06:14:00Z fw-change-882 applied to sg-pay-2 and nacl-pay-2 on subnet-pay-2\n"
        "2026-11-26T06:14:04Z subnet-pay-2 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=DROP\n"
        "2026-11-26T06:15:10Z DNS NOERROR 198.51.100.77; subnet-pay-1 TCP/443 ACCEPT + TLS cert valid until 2027-09-01\n",
        encoding="utf-8",
    )

    return {
        "final_text": (
            "Isolated the `edge-api` outage to `subnet-pay-2` egress TCP/443 `DROP` (`sg-pay-2`/`nacl-pay-2`, `fw-change-882`) "
            "amplified by an unbounded retry storm in `repo/src/gateway.py`, ruled out the unrelated `batch-analytics-pool` CPU warning decoy, "
            "saved scrubbed UTC-stamped logs and traces under `program/astack_home/edge-api/logging/{logs,traces}/`, wrote `program/INCIDENT_REPORT.md`, "
            "and hardened `repo/src/gateway.py` with bounded timeouts, jittered retries, header redaction, and low-cardinality metric labels."
        ),
    }
