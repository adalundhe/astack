#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests repo/docs

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

# Commit A: good base implementation + passing tests
cat > repo/src/rate_limit.py <<'EOF'
"""Fixed-window rate limiter."""
from __future__ import annotations


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[tuple[str, int], int] = {}

    def allow(self, key: str, now_seconds: float) -> bool:
        bucket = int(now_seconds // self.window_seconds)
        slot = (key, bucket)
        used = self._buckets.get(slot, 0)
        if used >= self.limit:
            return False
        self._buckets[slot] = used + 1
        return True
EOF

cat > repo/tests/test_rate_limit.py <<'EOF'
import unittest
from src.rate_limit import RateLimiter


class RateLimiterTest(unittest.TestCase):
    def test_enforces_exact_limit_per_window(self):
        rl = RateLimiter(limit=2, window_seconds=60)
        self.assertTrue(rl.allow("u1", 0.0))
        self.assertTrue(rl.allow("u1", 10.0))
        self.assertFalse(rl.allow("u1", 20.0))

    def test_resets_in_next_window(self):
        rl = RateLimiter(limit=1, window_seconds=60)
        self.assertTrue(rl.allow("u1", 59.0))
        self.assertFalse(rl.allow("u1", 59.5))
        self.assertTrue(rl.allow("u1", 60.0))


if __name__ == "__main__":
    unittest.main()
EOF

cat > repo/README.md <<'EOF'
# Rate Limiter Service

Fixed-window request limiter in `src/rate_limit.py`.
EOF

git -C repo add .
git -C repo commit -q -m "feat: add fixed-window rate limiter and tests"
git -C repo rev-parse HEAD > program/commit_a.txt

# Commit B: buggy change causing test failure
cat > repo/src/rate_limit.py <<'EOF'
"""Fixed-window rate limiter."""
from __future__ import annotations


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._buckets: dict[tuple[str, int], int] = {}

    def allow(self, key: str, now_seconds: float) -> bool:
        bucket = int(now_seconds // self.window_seconds)
        slot = (key, bucket)
        used = self._buckets.get(slot, 0)
        # Buggy off-by-one introduced during burst optimization: allows limit + 1 requests
        if used > self.limit:
            return False
        self._buckets[slot] = used + 1
        return True
EOF

git -C repo add repo/src/rate_limit.py 2>/dev/null || git -C repo add src/rate_limit.py
git -C repo commit -q -m "feat: optimize rate limit burst check"
git -C repo rev-parse HEAD > program/commit_b.txt

# Commit C: good unrelated documentation commit on top of Commit B
cat > repo/docs/API.md <<'EOF'
# Rate Limit HTTP Headers

All API endpoints return the following rate-limit headers:

- `X-RateLimit-Limit`: Maximum requests allowed in the active window.
- `X-RateLimit-Remaining`: Remaining requests before throttling.
- `Retry-After`: Seconds until the next window opens when HTTP 429 is returned.
EOF

cat >> repo/README.md <<'EOF'

See `docs/API.md` for HTTP response header definitions.
EOF

git -C repo add docs/API.md README.md
git -C repo commit -q -m "docs: document rate-limit HTTP response headers"
git -C repo rev-parse HEAD > program/commit_c.txt
