#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/net_spec.py <<'EOF'
from __future__ import annotations

DEFAULT_HTTPS_PORT = 443  # RFC 9110
MAX_UDP_DNS_BYTES = 512  # RFC 1035
SHA256_BYTES = 32  # FIPS 180-4


def format_https_url(host: str, path: str = "/", port: int = DEFAULT_HTTPS_PORT) -> str:
    """Build a canonical HTTPS URL, omitting the port when it matches the RFC 9110 default."""
    cleaned_host = host.strip()
    if not cleaned_host:
        raise ValueError("host must not be empty")
    if not isinstance(port, int) or isinstance(port, bool) or not (1 <= port <= 65535):
        raise ValueError("port must be an integer in 1..65535")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"https://{cleaned_host}:{port}{normalized_path}"


def fits_classic_udp_dns(payload: bytes) -> bool:
    return len(payload) <= MAX_UDP_DNS_BYTES


def is_sha256_digest(digest: bytes) -> bool:
    return len(digest) == SHA256_BYTES
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_net_spec.py <<'EOF'
import unittest

from src.net_spec import (
    DEFAULT_HTTPS_PORT,
    MAX_UDP_DNS_BYTES,
    SHA256_BYTES,
    fits_classic_udp_dns,
    format_https_url,
    is_sha256_digest,
)


class NetSpecTest(unittest.TestCase):
    def test_omits_default_https_port(self):
        self.assertEqual(
            format_https_url("api.example.invalid", "/v1/health"),
            "https://api.example.invalid/v1/health",
        )
        self.assertEqual(
            format_https_url("api.example.invalid", "v1/health", port=DEFAULT_HTTPS_PORT),
            "https://api.example.invalid/v1/health",
        )

    def test_preserves_non_default_https_port(self):
        self.assertEqual(
            format_https_url("api.example.invalid", "v1/health", port=8443),
            "https://api.example.invalid:8443/v1/health",
        )

    def test_protocol_helpers(self):
        self.assertTrue(fits_classic_udp_dns(b"a" * MAX_UDP_DNS_BYTES))
        self.assertFalse(fits_classic_udp_dns(b"a" * (MAX_UDP_DNS_BYTES + 1)))
        self.assertTrue(is_sha256_digest(b"\x00" * SHA256_BYTES))
        self.assertFalse(is_sha256_digest(b"\x00" * (SHA256_BYTES - 1)))


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
