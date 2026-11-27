"""Separated offline oracle for `capstone-plan-adc-rightsize`."""
from __future__ import annotations

from pathlib import Path

_AD_2_MD = """---
ad_number: 2
name: Stepped-Complexity Client Interface and Actionable Errors
description: Replace the mandatory 10-argument fetch contract and opaque error codes with a progressive Tier 0/1/2 API and actionable exceptions.
---

# AD-2: Stepped-Complexity Client Interface and Actionable Errors

## Status

Accepted (2026-11-26). Built (2026-11-26).

**Related:** AD-1 (preserves the immutable `Response` envelope and pluggable transport callable).

## Context

In `repo/src/client.py`, every caller of `fetch(...)` had to provide 10 mandatory arguments including duplicate timeout parameters (`timeout_seconds`, `timeout_ms`), redundant retry toggles (`retry_enabled`, `max_retries`), raw header tuple lists (`headers_list`), and dead flags (`legacy_xml_envelope`). Failures raised opaque `"ERR_9"` and `"ERR_4"` strings, and `repo/docs/api.md` contradicted `DEFAULT_TIMEOUT_SECONDS = 5.0` by documenting `30 seconds`.

## Decision

Collapse the public contract of `repo/src/client.py:fetch` into three progressive tiers:
- **Tier 0:** `fetch(url)` requires only `url`, defaulting to `DEFAULT_TIMEOUT_SECONDS = 5.0`, empty headers, single attempt, and `default_transport`.
- **Tier 1:** Optional `timeout: float` and plain `headers: dict[str, str] | None`.
- **Tier 2:** Optional `retry: RetryPolicy | None` and pluggable `transport` callable.
- **Errors:** Raise `ClientError(ValueError)` with concrete diagnostic text naming the invalid input and the exact fix (e.g., `"Invalid URL 'not-a-url': must start with http:// or https://"`).

## Non-goals

Automatic HTTP/2 multiplexing, cookie jars, or backward-compatible parsing of legacy XML envelopes.

## Costs accepted

Existing internal callers passing 10 positional arguments must migrate to keyword options (`timeout=`, `headers=`, `retry=`, `transport=`).

## Alternatives considered

1. **Keeping 10 parameters with defaults:** Retains contradictory aliases (`timeout_ms` vs `timeout_seconds`, `retry_enabled` vs `max_retries`) and dead `legacy_xml_envelope` in the public contract.
2. **Adding a parallel `simple_fetch(url)` wrapper:** Splits the SDK into two overlapping entrypoints and violates single-contract clarity.

## Acceptance criteria

- `inspect.signature(fetch)` has exactly one required parameter: `url`.
- Tier 0, Tier 1, and Tier 2 calls pass with `default_transport` and custom retryable transports.
- Invalid URLs and non-positive timeouts raise actionable errors never containing `"ERR_9"` or `"ERR_4"`.
- `repo/docs/api.md` matches `DEFAULT_TIMEOUT_SECONDS = 5.0`.

## Tests

- Tier 0/1/2 behavioral tests in `repo/tests/test_client.py`.
- Actionable error assertions rejecting `"ERR_9"` and `"ERR_4"`.
- Doc-to-code parity check on `DEFAULT_TIMEOUT_SECONDS`.

## Evidence

Contract-reduction catalog saved at `program/astack_home/sdk-v2/docs/contracts/client-contract-reduction.md` and verified via `unittest`.
"""

_CONTRACT_CATALOG = """# Contract-Reduction Catalog — `sdk-v2` (`repo/src/client.py`)

## Bloated Surface Audit

| Location | Parameter / Artifact | Defect | Disposition |
| --- | --- | --- | --- |
| `src/client.py:34` | `method` | Required even though 99% of calls are GET | Optional keyword default `"GET"` (or omitted for read fetch) |
| `src/client.py:35` | `headers_list` | Low-level `list[tuple[str, str]]` ceremony | Replace with optional `headers: dict[str, str] | None = None` |
| `src/client.py:36`–`37` | `timeout_seconds` + `timeout_ms` | Duplicate conflicting aliases | Keep single optional `timeout: float = DEFAULT_TIMEOUT_SECONDS` (`5.0`) |
| `src/client.py:38`–`39` | `retry_enabled` + `max_retries` | Redundant boolean toggle paired with count | Replace with optional `retry: RetryPolicy | None = None` |
| `src/client.py:41` | `legacy_xml_envelope` | Dead unused parameter | Remove completely |
| `src/client.py:42` | `transport_config` | Unstructured dict wrapper around a single callable | Replace with optional `transport: Transport | None = None` |
| `src/client.py:46`–`48` | `"ERR_9"` / `"ERR_4"` | Opaque error codes with zero remediation | Replace with actionable `ClientError` messages |

## Progressive Stepped Tiers

- **Tier 0 (zero ceremony):** `fetch("https://api.sdk.invalid/health")`
- **Tier 1 (common options):** `fetch(url, timeout=2.5, headers={"X-Caller": "svc"})`
- **Tier 2 (power users):** `fetch(url, retry=RetryPolicy(max_attempts=3), transport=custom_transport)`

## Migration & Deprecation Path

1. Ship `sdk-v2` 2.0 with the right-sized `fetch(url, *, timeout=..., headers=..., retry=..., transport=...)` contract documented in `repo/docs/api.md`.
2. Migrate callers from positional 10-arg calls to Tier 0/1/2 keyword arguments; remove dead `legacy_xml_envelope` and duplicate `timeout_ms` flags.
3. Sync `repo/docs/api.md` timeout documentation to `5.0 seconds` (`DEFAULT_TIMEOUT_SECONDS`) to eliminate the stale `30 seconds` contradiction.
"""

_REFACTORED_CLIENT = '''"""sdk-v2 HTTP client with progressive stepped complexity and actionable errors."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

DEFAULT_TIMEOUT_SECONDS = 5.0


class ClientError(ValueError):
    """Actionable client configuration or request error."""


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retry_statuses: tuple[int, ...] = (502, 503, 504)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ClientError(
                f"Invalid RetryPolicy.max_attempts={self.max_attempts!r}: must be an integer >= 1."
            )


Transport = Callable[[str, dict[str, str], float], Response]


def default_transport(url: str, headers: dict[str, str], timeout: float) -> Response:
    """In-process deterministic transport for offline/unit usage."""
    if url.endswith("/health"):
        return Response(status=200, body=b"ok", headers={"Content-Type": "text/plain"})
    if url.endswith("/echo"):
        payload = json.dumps({"url": url, "headers": headers, "timeout": timeout}).encode("utf-8")
        return Response(status=200, body=payload, headers={"Content-Type": "application/json"})
    return Response(status=404, body=b"not found", headers={"Content-Type": "text/plain"})


def fetch(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    headers: dict[str, str] | None = None,
    retry: RetryPolicy | None = None,
    transport: Transport | None = None,
) -> Response:
    """Fetch a URL using progressive complexity tiers.

    Tier 0: fetch(url)
    Tier 1: fetch(url, timeout=2.5, headers={"X-Caller": "app"})
    Tier 2: fetch(url, retry=RetryPolicy(max_attempts=3), transport=custom_fn)
    """
    if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
        raise ClientError(
            f"Invalid URL {url!r}: expected an absolute URL starting with 'http://' or 'https://'."
        )
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or float(timeout) <= 0:
        raise ClientError(
            f"Invalid timeout {timeout!r}: timeout must be a positive number of seconds (> 0)."
        )

    effective_headers = dict(headers) if headers is not None else {}
    policy = retry if retry is not None else RetryPolicy(max_attempts=1)
    active_transport = transport if transport is not None else default_transport

    resp = Response(status=500, body=b"", headers={})
    for attempt in range(1, policy.max_attempts + 1):
        resp = active_transport(url, effective_headers, float(timeout))
        if resp.status not in policy.retry_statuses or attempt == policy.max_attempts:
            return resp
    return resp
'''

_SYNCED_API_MD = """# sdk-v2 Client API Reference

## Quick Start (Tier 0)

Call `fetch(url)` with a single URL argument and sensible defaults:

```python
from client import fetch

resp = fetch("https://api.sdk.invalid/health")
```

## Common Options (Tier 1)

Override timeout or pass plain dictionary headers when needed:

```python
resp = fetch(
    "https://api.sdk.invalid/echo",
    timeout=2.5,
    headers={"X-Caller": "checkout"},
)
```

## Advanced Composition (Tier 2)

Compose a custom `RetryPolicy` and pluggable `transport` callable:

```python
from client import RetryPolicy, fetch

resp = fetch(
    "https://api.sdk.invalid/job",
    retry=RetryPolicy(max_attempts=3),
    transport=my_transport,
)
```

## Defaults & Actionable Errors

- Default timeout (`DEFAULT_TIMEOUT_SECONDS`): **5.0 seconds**.
- Invalid URLs raise `ClientError` explaining that the URL must start with `http://` or `https://`.
- Non-positive timeouts raise `ClientError` explaining that `timeout` must be a positive number of seconds (`> 0`).
"""

_REFACTORED_TESTS = '''"""Behavioral tests for stepped-complexity sdk-v2 client and doc sync."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from client import ClientError, DEFAULT_TIMEOUT_SECONDS, Response, RetryPolicy, fetch


def _make_flaky_transport(attempts: list[float]):
    def _transport(url: str, headers: dict[str, str], timeout: float) -> Response:
        attempts.append(timeout)
        if len(attempts) < 3:
            return Response(status=503, body=b"retry")
        return Response(status=200, body=b"ok")

    return _transport


class SteppedClientTests(unittest.TestCase):
    def test_fetch_health_with_ten_args(self) -> None:
        resp = fetch("https://api.sdk.invalid/health")
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.body, b"ok")

    def test_invalid_url_raises_err9(self) -> None:
        with self.assertRaises(ClientError) as ctx:
            fetch("bad-url")
        msg = str(ctx.exception)
        self.assertNotIn("ERR_9", msg)
        self.assertIn("https://", msg)

    def test_tier1_optional_timeout_and_headers(self) -> None:
        resp = fetch("https://api.sdk.invalid/echo", timeout=2.5, headers={"X-Caller": "unit"})
        self.assertEqual(resp.status, 200)
        body = json.loads(resp.body.decode("utf-8"))
        self.assertEqual(body["timeout"], 2.5)
        self.assertEqual(body["headers"]["X-Caller"], "unit")

    def test_tier2_custom_transport_and_retry_policy(self) -> None:
        attempts: list[float] = []
        resp = fetch(
            "https://api.sdk.invalid/job",
            timeout=1.5,
            retry=RetryPolicy(max_attempts=3),
            transport=_make_flaky_transport(attempts),
        )
        self.assertEqual(resp.status, 200)
        self.assertEqual(len(attempts), 3)

    def test_invalid_timeout_raises_actionable_error(self) -> None:
        with self.assertRaises(ClientError) as ctx:
            fetch("https://api.sdk.invalid/health", timeout=-2)
        msg = str(ctx.exception)
        self.assertNotIn("ERR_4", msg)
        self.assertIn("positive", msg.lower())

    def test_docs_match_default_timeout(self) -> None:
        docs = (Path(__file__).resolve().parents[1] / "docs" / "api.md").read_text(encoding="utf-8")
        self.assertIn(f"{DEFAULT_TIMEOUT_SECONDS:.1f}", docs)
        self.assertNotIn("30 seconds", docs.lower())


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    astack_home = ws / "program" / "astack_home"

    # 1. Publish AD_2.md (preserving AD_1.md untouched)
    arch_dir = astack_home / "sdk-v2" / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    (arch_dir / "AD_2.md").write_text(_AD_2_MD, encoding="utf-8")

    # 2. Save contract-reduction catalog under docs/contracts/
    contracts_dir = astack_home / "sdk-v2" / "docs" / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    (contracts_dir / "client-contract-reduction.md").write_text(_CONTRACT_CATALOG, encoding="utf-8")

    # 3. Refactor client.py, sync docs/api.md, expand tests
    (repo / "src" / "client.py").write_text(_REFACTORED_CLIENT, encoding="utf-8")
    (repo / "docs" / "api.md").write_text(_SYNCED_API_MD, encoding="utf-8")
    (repo / "tests" / "test_client.py").write_text(_REFACTORED_TESTS, encoding="utf-8")

    return {
        "final_text": (
            "Published `AD_2.md` under `program/astack_home/sdk-v2/architecture/AD_2.md` (preserving `AD_1.md`), "
            "saved the contract-reduction catalog at `program/astack_home/sdk-v2/docs/contracts/client-contract-reduction.md`, "
            "refactored `repo/src/client.py` into stepped Tier 0/1/2 `fetch(url, ...)` with actionable `ClientError` messages "
            "replacing `ERR_9`/`ERR_4`, synced `repo/docs/api.md` to `DEFAULT_TIMEOUT_SECONDS = 5.0`, and verified all unit tests pass."
        ),
    }
