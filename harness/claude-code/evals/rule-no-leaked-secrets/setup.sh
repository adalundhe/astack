#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Billing API Connector

Provides `ConnectorError`, `redact_text`, `redact_headers`, and `ApiConnector` in `src/connector.py`.

## Contract
- `ApiConnector(base_url: str, api_key: str, *, transport=None, logger: logging.Logger | None = None)`:
  - Must require a non-empty `api_key` (no hardcoded credentials in source).
  - Sends `Authorization: Bearer <api_key>` and `X-Correlation-Id: <correlation_id>` to `transport(url, headers) -> tuple[int, str]`.
- `fetch_account(account_id: str, *, correlation_id: str = "req-1") -> dict`:
  - Returns parsed JSON dict on HTTP 200.
  - On HTTP >= 400 or transport exception, raises `ConnectorError` containing `correlation_id` and HTTP status / error type, with ZERO raw credentials, `Authorization` values, or secret tokens in the error message, logs, or stderr.
- `debug_snapshot() -> dict`:
  - Returns safe diagnostic metadata (`base_url`, redacted headers / credential state) with ZERO raw API key or bearer token values.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/connector.py <<'EOF'
from __future__ import annotations

import json
import logging
import sys
from typing import Any, Callable

DEFAULT_API_KEY = "sk-live-9876543210abcdef"


class ConnectorError(RuntimeError):
    """Raised when an upstream API request fails."""


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return dict(headers)


class ApiConnector:
    def __init__(
        self,
        base_url: str,
        api_key: str = DEFAULT_API_KEY,
        *,
        transport: Callable[[str, dict[str, str]], tuple[int, str]] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._transport = transport
        self._logger = logger or logging.getLogger("billing.connector")

    def _headers(self, correlation_id: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "X-Correlation-Id": correlation_id,
            "Accept": "application/json",
        }

    def debug_snapshot(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "api_key": self._api_key,
            "headers": self._headers("debug"),
        }

    def fetch_account(self, account_id: str, *, correlation_id: str = "req-1") -> dict[str, Any]:
        if self._transport is None:
            raise ConnectorError(f"no transport configured for {self.base_url} key={self._api_key}")
        url = f"{self.base_url}/accounts/{account_id}"
        headers = self._headers(correlation_id)
        self._logger.info("fetching url=%s headers=%s", url, headers)
        try:
            status, body = self._transport(url, headers)
        except Exception as exc:
            print(f"ERROR request failed headers={headers} err={exc}", file=sys.stderr)
            self._logger.error("request failed headers=%s err=%s", headers, exc)
            raise ConnectorError(
                f"transport failed correlation_id={correlation_id} key={self._api_key} err={exc}"
            ) from exc

        if status >= 400:
            print(f"ERROR status={status} headers={headers} body={body}", file=sys.stderr)
            self._logger.error("upstream error status=%s headers=%s body=%s", status, headers, body)
            raise ConnectorError(
                f"upstream HTTP {status} correlation_id={correlation_id} headers={headers} body={body}"
            )
        return json.loads(body)
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_connector.py <<'EOF'
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from connector import ApiConnector


class ConnectorBaselineTest(unittest.TestCase):
    def test_fetch_account_returns_payload_on_200(self):
        seen = {}

        def fake_transport(url, headers):
            seen["url"] = url
            seen["headers"] = dict(headers)
            return (200, json.dumps({"account_id": "acct-1", "tier": "pro"}))

        conn = ApiConnector("https://api.example.invalid", "test-token-not-real", transport=fake_transport)
        data = conn.fetch_account("acct-1", correlation_id="corr-1")
        self.assertEqual(data, {"account_id": "acct-1", "tier": "pro"})
        self.assertEqual(seen["headers"]["Authorization"], "Bearer test-token-not-real")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial api connector with leaked credentials"
