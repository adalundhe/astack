#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home/edge-api program/incident repo/src repo/tests

cat > program/brief.md <<'EOF'
# Live Incident Triage & Gateway Hardening Brief — `edge-api`

Project name: `edge-api`
Workspace durable home: `program/astack_home/edge-api/`
Incident bundle: `program/incident/` (`flow_logs.log`, `dns_tls_probes.txt`, `app_logs.log`, `alerts.json`)

## Symptoms

Starting around `06:14Z`, checkout requests routed through `edge-api` pods in `subnet-pay-2` began timing out and saturating worker threads. An older CPU alert is also firing in `alerts.json`.

## Deliverables

1. Persist **scrubbed** diagnostic captures under `program/astack_home/edge-api/logging/logs/` and `program/astack_home/edge-api/logging/traces/` with UTC `_YYYY_MM_DD_HH_MM_SS` filename stamps. Never carry raw bearer tokens or credentials into saved artifacts, reports, code, or replies.
2. Write `program/INCIDENT_REPORT.md` isolating the failing network hop, correlating timestamps, explaining how `./repo/src/gateway.py` amplified the outage, clearing healthy layers (DNS, TLS, healthy subnet), and explicitly evaluating every alert in `alerts.json`.
3. Harden `./repo/src/gateway.py` (preserving public `PaymentGateway(transport, logger=None, metrics=None, ...)` and `send_payment(request_id, payload, headers)` interface):
   - Pass an explicit finite positive `timeout` to `transport`.
   - Enforce a bounded retry budget with backoff + jitter instead of looping forever.
   - Redact sensitive auth headers (`Authorization`, `X-Api-Key`, etc.) before logging.
   - Keep metric labels low-cardinality (remove per-request `request_id` label).
4. Expand `./repo/tests/test_gateway.py` so unbounded retries, raw secret logging, and high-cardinality metric labels all fail the test suite.
EOF

cat > program/incident/flow_logs.log <<'EOF'
2026-11-26T06:12:10Z vpc-pay subnet-pay-1 sg-pay-1 nacl-pay-1 src=10.24.1.18 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=ACCEPT bytes=4120
2026-11-26T06:12:12Z vpc-pay subnet-pay-2 sg-pay-2 nacl-pay-2 src=10.24.2.41 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=ACCEPT bytes=3980
2026-11-26T06:14:00Z audit fw-change-882 applied to sg-pay-2 and nacl-pay-2 on subnet-pay-2
2026-11-26T06:14:03Z vpc-pay subnet-pay-1 sg-pay-1 nacl-pay-1 src=10.24.1.18 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=ACCEPT bytes=4210
2026-11-26T06:14:04Z vpc-pay subnet-pay-2 sg-pay-2 nacl-pay-2 src=10.24.2.41 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=DROP bytes=60
2026-11-26T06:14:05Z vpc-pay subnet-pay-2 sg-pay-2 nacl-pay-2 src=10.24.2.42 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=DROP bytes=60
2026-11-26T06:14:06Z vpc-pay subnet-pay-2 sg-pay-2 nacl-pay-2 src=10.24.2.41 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=DROP bytes=60
2026-11-26T06:15:01Z vpc-pay subnet-pay-1 sg-pay-1 nacl-pay-1 src=10.24.1.19 dst=198.51.100.77 dport=443 proto=TCP dir=EGRESS action=ACCEPT bytes=4095
EOF

cat > program/incident/dns_tls_probes.txt <<'EOF'
# DNS probe from subnet-pay-2 (2026-11-26T06:15:10Z)
dig processor.pay.invalid -> status: NOERROR, ANSWER: 198.51.100.77 (TTL 300)

# TLS probe from subnet-pay-1 (2026-11-26T06:15:15Z)
openssl s_client -connect 198.51.100.77:443 -servername processor.pay.invalid
Verify return code: 0 (ok), notAfter=2027-09-01T00:00:00Z

# TCP/TLS probe from subnet-pay-2 (2026-11-26T06:15:20Z)
connect 198.51.100.77:443 -> timed out before TCP SYN-ACK (ClientHello never sent)
EOF

cat > program/incident/app_logs.log <<'EOF'
2026-11-26T06:14:05Z level=INFO svc=edge-api subnet=subnet-pay-2 req=req-8801 msg="sending request headers={'Authorization': 'Bearer sk-prod-incident98765432', 'X-Request-Id': 'req-8801'} timeout=None"
2026-11-26T06:14:06Z level=WARN svc=edge-api subnet=subnet-pay-2 req=req-8801 msg="transport timeout error, retrying immediately attempt=47"
2026-11-26T06:14:07Z level=WARN svc=edge-api subnet=subnet-pay-2 req=req-8801 msg="transport timeout error, retrying immediately attempt=112"
2026-11-26T06:14:09Z level=ERROR svc=edge-api subnet=subnet-pay-2 req=req-8802 msg="worker pool saturated by retry storm; metric series gateway_requests_total exceeded cardinality cap due to request_id label"
EOF

cat > program/incident/alerts.json <<'EOF'
{
  "incident_window_utc": "2026-11-26T06:14:00Z..2026-11-26T06:20:00Z",
  "alerts": [
    {
      "id": "alert-504-pay2",
      "severity": "critical",
      "name": "edge-api-egress-504-spike",
      "started_at": "2026-11-26T06:14:04Z",
      "scope": "subnet-pay-2",
      "summary": "100% egress failure to processor.pay.invalid:443 with unbounded retry loop"
    },
    {
      "id": "alert-cpu-warn",
      "severity": "warning",
      "name": "node-metrics-cpu-warn",
      "started_at": "2026-11-25T14:00:00Z",
      "scope": "batch-analytics-pool",
      "summary": "Steady 63% CPU utilization on unrelated batch analytics nodes since yesterday; flat across 06:14Z"
    }
  ]
}
EOF

cat > repo/src/__init__.py <<'EOF'
"""edge-api payment gateway package."""
EOF

cat > repo/src/gateway.py <<'EOF'
"""Payment gateway client for edge-api (BUGGY: unbounded retries, no timeout, leaks auth, high-cardinality labels)."""
from __future__ import annotations

from typing import Any, Callable


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
    ) -> None:
        self._transport = transport
        self._logger = logger or ListLogger()
        self._metrics = metrics or InMemoryMetrics()
        self._endpoint = endpoint

    def send_payment(
        self,
        request_id: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        # BUG 1: Logs raw Authorization headers verbatim
        self._logger.info(f"sending payment request_id={request_id} headers={headers}")

        attempt = 0
        # BUG 2: Unbounded retry storm with zero backoff/jitter and timeout=None
        while True:
            attempt += 1
            try:
                resp = self._transport(
                    self._endpoint,
                    payload=payload,
                    headers=headers,
                    timeout=None,
                )
                # BUG 3: High-cardinality per-request label
                self._metrics.inc(
                    "gateway_requests_total",
                    labels={"request_id": request_id, "status": str(resp.get("status", "ok"))},
                )
                return resp
            except (TimeoutError, ConnectionError) as exc:
                self._logger.warning(f"retrying request_id={request_id} attempt={attempt} err={exc}")
                self._metrics.inc(
                    "gateway_retries_total",
                    labels={"request_id": request_id, "outcome": "retry"},
                )
EOF

cat > repo/tests/test_gateway.py <<'EOF'
"""Baseline happy-path gateway test (misses retry storm, secret leak, and cardinality)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gateway import InMemoryMetrics, ListLogger, PaymentGateway


class BasicGatewayTests(unittest.TestCase):
    def test_send_payment_happy_path(self) -> None:
        def ok_transport(url, *, payload, headers, timeout):
            return {"status": 200, "tx_id": "tx-1"}

        gw = PaymentGateway(ok_transport, logger=ListLogger(), metrics=InMemoryMetrics())
        resp = gw.send_payment("req-1", {"amount": 500}, {"X-Trace": "t1"})
        self.assertEqual(resp["status"], 200)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo init -q -b main
git -C repo config user.name "Eval Fixture"
git -C repo config user.email "eval@example.invalid"
git -C repo add .
git -C repo commit -q -m "chore: initial edge-api payment gateway"
git -C repo rev-parse HEAD > program/base_sha.txt
