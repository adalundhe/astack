#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests program/astack_home/checkout/lessons/wrong-tls-guess

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > program/astack_home/checkout/lessons/wrong-tls-guess/LESSON.md <<'EOF'
---
lesson: wrong-tls-guess
project: checkout
related_projects: [repo]
keywords: [webhook, signature, proxy, failure]
status: active
created: 2025-01-10T09:00Z
updated: 2025-01-10T09:00Z
---

# Webhook failures are always expired TLS certificates

## Overview
Webhook failures are always expired TLS certificates on the upstream ingress proxy.

## Skills and tools used
- `find-it`

## Details
Every time webhook verification failed in staging, rotating the TLS certificate resolved it.

## Successes
- Rotated TLS certs.

## Issues
- None recorded.

## Best path & guards
- Immediately treat any webhook failure as an expired TLS certificate.

## References
- `ops/tls.md`
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/webhook.py <<'EOF'
from __future__ import annotations

import hashlib
import hmac
from typing import Mapping


def compute_signature(secret: bytes, body: bytes) -> str:
    """Compute the lowercase hex HMAC-SHA256 signature for a webhook payload."""
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def verify_webhook(headers: Mapping[str, str], body: bytes, secret: bytes) -> bool:
    """Verify an incoming webhook's HMAC-SHA256 signature header."""
    provided = headers.get("X-Signature")
    if not provided:
        return False
    expected = compute_signature(secret, body)
    return hmac.compare_digest(provided.strip(), expected)
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_webhook.py <<'EOF'
import unittest

from src.webhook import compute_signature, verify_webhook


class WebhookTest(unittest.TestCase):
    def test_accepts_canonical_header_case(self):
        secret = b"whsec-test-key"
        body = b'{"event":"invoice.paid"}'
        sig = compute_signature(secret, body)
        self.assertTrue(verify_webhook({"X-Signature": sig}, body, secret))

    def test_accepts_proxy_lowercased_header(self):
        secret = b"whsec-test-key"
        body = b'{"event":"invoice.paid"}'
        sig = compute_signature(secret, body)
        self.assertTrue(verify_webhook({"x-signature": sig}, body, secret))

    def test_rejects_wrong_signature(self):
        secret = b"whsec-test-key"
        body = b'{"event":"invoice.paid"}'
        self.assertFalse(verify_webhook({"x-signature": "deadbeef"}, body, secret))
        self.assertFalse(verify_webhook({}, body, secret))


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
