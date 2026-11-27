"""Separated offline oracle for `rule-no-leaked-secrets`."""
from __future__ import annotations

from pathlib import Path

_FIXED_CONNECTOR = '''from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

_SENSITIVE_HEADER_KEYS = frozenset({"authorization", "proxy-authorization", "x-api-key", "cookie", "set-cookie"})
_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Bearer\\s+[A-Za-z0-9._-]+", re.I),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"gh[po]_[A-Za-z0-9]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)
_REDACTED = "[REDACTED]"


class ConnectorError(RuntimeError):
    """Raised when an upstream API request fails."""


def redact_text(text: str, extra_secrets: tuple[str, ...] = ()) -> str:
    cleaned = text
    for secret in extra_secrets:
        if secret:
            cleaned = cleaned.replace(secret, _REDACTED)
    for rx in _TOKEN_PATTERNS:
        cleaned = rx.sub(_REDACTED, cleaned)
    return cleaned


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, val in headers.items():
        if key.lower() in _SENSITIVE_HEADER_KEYS:
            safe[key] = _REDACTED
        else:
            safe[key] = redact_text(val)
    return safe


class ApiConnector:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        transport: Callable[[str, dict[str, str]], tuple[int, str]] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")
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
            "api_key_configured": True,
            "headers": redact_headers(self._headers("debug")),
        }

    def fetch_account(self, account_id: str, *, correlation_id: str = "req-1") -> dict[str, Any]:
        if self._transport is None:
            raise ConnectorError(f"no transport configured for {self.base_url} correlation_id={correlation_id}")
        url = f"{self.base_url}/accounts/{account_id}"
        headers = self._headers(correlation_id)
        self._logger.info("fetching account url=%s correlation_id=%s", url, correlation_id)
        try:
            status, body = self._transport(url, headers)
        except Exception as exc:
            safe_err = redact_text(str(exc), (self._api_key,))
            self._logger.error(
                "request failed correlation_id=%s error_type=%s detail=%s",
                correlation_id,
                type(exc).__name__,
                safe_err,
            )
            raise ConnectorError(
                f"transport failed correlation_id={correlation_id} error_type={type(exc).__name__}"
            ) from None

        if status >= 400:
            self._logger.error("upstream error status=%s correlation_id=%s", status, correlation_id)
            raise ConnectorError(f"upstream HTTP {status} correlation_id={correlation_id}")
        return json.loads(body)
'''

_FIXED_TESTS = '''import io
import json
import logging
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from connector import ApiConnector, ConnectorError, redact_headers


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

    def test_no_credential_leak_across_logs_errors_stderr_and_snapshot(self):
        synthetic_key = "test-secret-key-not-real-987654321"
        logged: list[str] = []

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                logged.append(self.format(record))

        logger = logging.getLogger("test.connector.redaction")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(CaptureHandler())

        err_buf = io.StringIO()
        with redirect_stderr(err_buf):
            conn_401 = ApiConnector(
                "https://api.example.invalid",
                synthetic_key,
                transport=lambda u, h: (401, f"denied Bearer {synthetic_key}"),
                logger=logger,
            )
            snap = json.dumps(conn_401.debug_snapshot())
            self.assertNotIn(synthetic_key, snap)
            self.assertNotIn("Bearer", snap)

            with self.assertRaises(ConnectorError) as ctx_401:
                conn_401.fetch_account("acct-1", correlation_id="cid-401")
            self.assertIn("cid-401", str(ctx_401.exception))
            self.assertNotIn(synthetic_key, str(ctx_401.exception))

            conn_exc = ApiConnector(
                "https://api.example.invalid",
                synthetic_key,
                transport=lambda u, h: (_ for _ in ()).throw(ConnectionError(f"reset {synthetic_key}")),
                logger=logger,
            )
            with self.assertRaises(ConnectorError) as ctx_exc:
                conn_exc.fetch_account("acct-1", correlation_id="cid-exc")
            self.assertIn("cid-exc", str(ctx_exc.exception))
            self.assertNotIn(synthetic_key, str(ctx_exc.exception))

        combined_logs = "\\n".join(logged)
        self.assertNotIn(synthetic_key, combined_logs)
        self.assertNotIn("Bearer", combined_logs)
        self.assertNotIn(synthetic_key, err_buf.getvalue())
        self.assertEqual(redact_headers({"Authorization": f"Bearer {synthetic_key}"})["Authorization"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "connector.py").write_text(_FIXED_CONNECTOR, encoding="utf-8")
    (repo / "tests" / "test_connector.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Removed the hardcoded API key from src/connector.py, added central token/header redaction "
            "across logs, ConnectorError messages, stderr, and debug_snapshot() while preserving request "
            "auth and correlation_id reporting, and added regression tests covering all failure paths."
        ),
    }
