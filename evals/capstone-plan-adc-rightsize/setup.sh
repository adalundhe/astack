#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home/sdk-v2/architecture repo/src repo/docs repo/tests

cat > program/astack_home/sdk-v2/architecture/AD_1.md <<'EOF'
---
ad_number: 1
name: Deterministic Transport Wire Envelope
description: Use JSON-encoded request and response envelopes over pluggable in-process or HTTP transports.
---

# AD-1: Deterministic Transport Wire Envelope

## Status

Accepted (2026-10-12). Built (2026-10-15).

## Context

`sdk-v2` callers need deterministic request/response objects for both production HTTP and offline unit tests without spawning loopback servers.

## Decision

Represent responses with an immutable `Response(status, body, headers)` dataclass and accept pluggable transport callables returning `Response`.

## Non-goals

Transport connection pooling and TLS cipher negotiation.

## Costs accepted

Callers writing custom transports must normalize header keys and return `Response`.

## Alternatives considered

Hard-coding `urllib.request` directly inside `client.py` made offline tests brittle and slow.

## Acceptance criteria

`Response` preserves `status: int`, `body: bytes`, and `headers: dict[str, str]`.

## Tests

Transport envelope unit tests verify status, body bytes, and header preservation.

## Evidence

Adopted across `sdk-v2` 1.0 release.
EOF

/opt/homebrew/bin/python3.12 -B - <<'PYEOF'
import hashlib
from pathlib import Path
ad1 = Path("program/astack_home/sdk-v2/architecture/AD_1.md")
Path("program/ad1_sha256.txt").write_text(hashlib.sha256(ad1.read_bytes()).hexdigest() + "\n", encoding="utf-8")
PYEOF

cat > program/brief.md <<'EOF'
# SDK Redesign & Contract Consolidation Brief — `sdk-v2`

Project name: `sdk-v2`
Workspace durable home: `program/astack_home/sdk-v2/`

## Current Problems

1. **Bloated 10-argument mandatory interface (`./repo/src/client.py`):**
   Every caller of `fetch(...)` must supply 10 mandatory arguments including duplicate aliases (`timeout_seconds` + `timeout_ms`, `retry_enabled` + `max_retries`), raw tuple lists (`headers_list`), dead legacy flags (`legacy_xml_envelope`), and raw transport configuration (`transport_config`).
2. **Cryptic errors:**
   Invalid URLs raise `RuntimeError("ERR_9")` and invalid timeouts raise `RuntimeError("ERR_4")` with no explanation of what failed or how to fix it.
3. **Documentation contradiction (`./repo/docs/api.md` vs `./repo/src/client.py`):**
   `repo/docs/api.md` states the default timeout is `30 seconds`, whereas `src/client.py` defines `DEFAULT_TIMEOUT_SECONDS = 5.0` and still forces callers to pass timeouts explicitly.

## Deliverables

1. **Architecture Decision (`program/astack_home/sdk-v2/architecture/AD_2.md`):**
   Preserve `AD_1.md` completely untouched and publish `AD_2.md` (no leftover `.draft.md`, never inside `./repo`) with valid YAML frontmatter (`ad_number: 2`, `name`, `description`) and all required sections (`Status`, `Context`, `Decision`, `Non-goals`, `Costs accepted`, `Alternatives considered`, `Acceptance criteria`, `Tests`, `Evidence`).
2. **Contract-reduction catalog (`program/astack_home/sdk-v2/docs/contracts/`):**
   Save a catalog citing `client.py:<line>` locations, auditing the redundant/dead parameters, defining progressive complexity tiers, and documenting the migration/deprecation path.
3. **Progressive API refactor (`./repo/src/client.py`):**
   - Tier 0: `fetch(url)` requires ONLY `url` and works with sensible defaults (`DEFAULT_TIMEOUT_SECONDS`, default GET method, in-process default transport).
   - Tier 1: optional `timeout` and plain `dict[str, str]` `headers`.
   - Tier 2: optional `retry` (`RetryPolicy(max_attempts=...)`) and custom `transport(url, headers, timeout)` callable.
   - Replace `"ERR_9"` / `"ERR_4"` with actionable errors stating both what failed and how to fix it.
4. **Sync docs (`./repo/docs/api.md`):**
   Match `src/client.py`'s actual signature, progressive usage examples, and exact `DEFAULT_TIMEOUT_SECONDS` (remove the stale `30 seconds` contradiction).
5. **Expand tests (`./repo/tests/test_client.py`):**
   Verify Tier 0, Tier 1, Tier 2, actionable error messages, and doc-to-code default parity.
EOF

cat > repo/src/__init__.py <<'EOF'
"""sdk-v2 client library."""
EOF

cat > repo/src/client.py <<'EOF'
"""sdk-v2 HTTP client (bloated 10-arg interface and cryptic error codes)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retry_statuses: tuple[int, ...] = (502, 503, 504)


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
    method: str,
    headers_list: list[tuple[str, str]],
    timeout_seconds: float,
    timeout_ms: int,
    retry_enabled: bool,
    max_retries: int,
    verify_tls: bool,
    legacy_xml_envelope: bool,
    transport_config: dict[str, Any],
) -> Response:
    """Bloated 10-arg mandatory interface with cryptic ERR_9 / ERR_4 failures."""
    if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
        raise RuntimeError("ERR_9")
    if timeout_seconds <= 0 or timeout_ms <= 0:
        raise RuntimeError("ERR_4")
    _ = (method, verify_tls, legacy_xml_envelope)
    transport: Callable[[str, dict[str, str], float], Response] = (
        transport_config.get("transport") or default_transport
    )
    hdrs = dict(headers_list)
    attempts = max(1, max_retries) if retry_enabled else 1
    resp = Response(status=500, body=b"", headers={})
    for _ in range(attempts):
        resp = transport(url, hdrs, float(timeout_seconds))
        if resp.status < 500:
            return resp
    return resp
EOF

cat > repo/docs/api.md <<'EOF'
# sdk-v2 Client API Reference

## `fetch(...)`

Callers must pass all 10 positional arguments:
`fetch(url, method, headers_list, timeout_seconds, timeout_ms, retry_enabled, max_retries, verify_tls, legacy_xml_envelope, transport_config)`.

### Defaults & Errors

- The default timeout is 30 seconds.
- Invalid URLs return `ERR_9`.
- Invalid timeouts return `ERR_4`.
EOF

cat > repo/tests/test_client.py <<'EOF'
"""Baseline tests locked to the bloated 10-arg interface and cryptic ERR_9 error."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from client import fetch


class BloatedClientTests(unittest.TestCase):
    def test_fetch_health_with_ten_args(self) -> None:
        resp = fetch(
            "https://api.sdk.invalid/health",
            "GET",
            [],
            5.0,
            5000,
            False,
            1,
            True,
            False,
            {},
        )
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.body, b"ok")

    def test_invalid_url_raises_err9(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "ERR_9"):
            fetch("bad-url", "GET", [], 5.0, 5000, False, 1, True, False, {})


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo init -q -b main
git -C repo config user.name "Eval Fixture"
git -C repo config user.email "eval@example.invalid"
git -C repo add .
git -C repo commit -q -m "chore: initial bloated 10-arg sdk-v2 client and contradictory docs"
git -C repo rev-parse HEAD > program/base_sha.txt
