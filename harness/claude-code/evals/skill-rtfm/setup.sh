#!/usr/bin/env bash
set -euo pipefail

mkdir -p program repo/docs repo/src

git -C repo init -q -b main
git -C repo config user.name "Original Author"
git -C repo config user.email "author@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/retry.py <<'EOF'
"""HTTP retry settings for upstream sync client."""
from __future__ import annotations

MAX_RETRIES = 5


def should_retry(attempt: int, status_code: int) -> bool:
    return attempt < MAX_RETRIES and status_code in (429, 502, 503, 504)
EOF

git -C repo add .
git -C repo commit -q -m "initial upstream retry helper with MAX_RETRIES=5"

cat > repo/src/retry.py <<'EOF'
"""HTTP retry settings for upstream sync client."""
from __future__ import annotations

MAX_RETRIES = 3


def should_retry(attempt: int, status_code: int) -> bool:
    return attempt < MAX_RETRIES and status_code in (429, 502, 503, 504)
EOF

cat > repo/docs/AD-007.md <<'EOF'
# AD-007: Cap Upstream Sync Retries at 3

## Status
Accepted

## Context
During the 2026-09 load incident, our worker retried rate-limited calls 5 times in a row.

## Decision
Set `MAX_RETRIES = 3` in `src/retry.py`.

## Rationale
Upstream enforces strict 429 ban on 4th attempt, locking out the client IP for 15 minutes. Stopping at 3 retries avoids triggering the ban while still absorbing transient 5xx glitches.
EOF

git -C repo add .
git -C repo commit -q -m "AD-007: cap MAX_RETRIES at 3 (Upstream enforces strict 429 ban on 4th attempt)"

cat > program/question.md <<'EOF'
Why is MAX_RETRIES 3? Should I ask the author?
EOF
