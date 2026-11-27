#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home program/sources repo/src

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/client.py <<'EOF'
"""Handshake header builder for proto-check client."""
from __future__ import annotations

import hashlib
import hmac

PROTO_VERSION = "2.1"


def build_handshake_headers(payload: bytes, signing_key: bytes) -> dict[str, str]:
    """Build v2.1 handshake headers using SHA-256 HMAC."""
    digest = hmac.new(signing_key, payload, hashlib.sha256).hexdigest()
    return {
        "X-Proto-Version": PROTO_VERSION,
        "X-Proto-Signature": f"sha256={digest}",
    }
EOF

git -C repo add .
git -C repo commit -q -m "implement v2.1 SHA-256 handshake client"

cat > program/sources/official-spec-v2.1.md <<'EOF'
# Proto-Check Wire Specification v2.1
Date: 2026-06-01
Author: Protocol Standards Committee (Official Specification)

## Section 4.2: Handshake Authentication
All v2.1 handshake requests MUST send header X-Proto-Version: 2.1 and use SHA-256 HMAC signatures; legacy MD5 signatures and X-Proto-Version: 1.0 were removed in v2.0.

## Section 4.3: Signature Header Format
The signature header MUST use `X-Proto-Signature: sha256=<hex_digest>`.
EOF

cat > program/sources/old-blog-2021.md <<'EOF'
# Quick Tips for Proto-Check Integrations
Date: 2021-03-14
Author: Alex Example (Personal Blog)

Clients should send X-Proto-Version: 1.0 and sign payloads with MD5 for maximum compatibility with older servers.
EOF

cat > program/question.md <<'EOF'
# Research Question (project: proto-check)

An engineer found `program/sources/old-blog-2021.md` recommending `X-Proto-Version: 1.0` with MD5 signatures, which conflicts with `program/sources/official-spec-v2.1.md` and `repo/src/client.py`.

Which handshake version header and signature algorithm should `proto-check` rely on? Resolve the conflict with verified quotes, source trust weights, explicit handling of the outdated counterclaim, and A–F graded findings saved under `$ASTACK_HOME/proto-check/research/`.
EOF
