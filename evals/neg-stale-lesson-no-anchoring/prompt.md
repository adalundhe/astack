---
description: "Negative control: an active but wrong prior lesson blaming expired TLS certificates does not anchor diagnosis when ./repo/src/webhook.py actually fails on case-sensitive X-Signature header lookup."
expected_outcome: "Fixes case-insensitive X-Signature header lookup in ./repo/src/webhook.py, adds mixed-case regression tests, and explains the real header-casing root cause without blaming expired TLS certificates."
timeout_seconds: 240
---

`/astack:go` Investigate why webhook verification is failing in `./repo/src/webhook.py` when requests pass through the reverse proxy (see the failing test in `./repo/tests/test_webhook.py`). Fix the root cause, add regression test coverage for mixed-case headers, and report the actual root cause in your summary.
