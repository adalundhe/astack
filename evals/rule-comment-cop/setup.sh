#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/rate_limiter.py <<'EOF'
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Acme Telemetry Inc. All rights reserved.
"""Sliding-window rate limiter for inbound API keys."""
from __future__ import annotations

from collections import deque
import math


# ============================================================
# RATE LIMITER IMPLEMENTATION
# ============================================================
class SlidingWindowLimiter:
    """Limits requests per key within a rolling window."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        # Check that max_requests is positive
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        # Check that window_seconds is positive
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        # Store configuration on self
        self.max_requests = max_requests
        self.window_seconds = float(window_seconds)
        # Initialize the buckets dictionary mapping keys to timestamp deques
        self._buckets: dict[str, deque[float]] = {}
        # Counter for total allowed requests
        self._allowed_count = 0

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------
    def _prune(self, key: str, now: float) -> deque[float]:
        # Get or create the deque for this key
        bucket = self._buckets.setdefault(key, deque())
        # Compute cutoff timestamp
        cutoff = now - self.window_seconds
        # Changed for ticket OPS-991: used to use list.pop(0) before 2024
        # Loop over timestamps to prune expired entries
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        # Return the pruned bucket
        return bucket

    def allow(self, key: str, now: float) -> bool:
        """Record a request at `now` and return True if within the limit."""
        bucket = self._prune(key, now)
        # old_limit = self.max_requests * 2
        # if len(bucket) >= old_limit:
        #     return False
        if len(bucket) >= self.max_requests:
            # Return False when limit exceeded
            return False
        # Append current timestamp
        bucket.append(now)
        # Increment request counter
        self._allowed_count += 1
        # Return True when allowed
        return True

    def retry_after_seconds(self, key: str, now: float) -> int:
        """Return whole seconds until the next request for `key` will be allowed."""
        bucket = self._prune(key, now)
        if len(bucket) < self.max_requests:
            return 0
        remaining = (bucket[0] + self.window_seconds) - now
        # RFC 6585 / upstream-proxy#4182: Retry-After must be rounded up to whole
        # seconds because Envoy 1.29 rejects fractional Retry-After headers.
        return max(1, math.ceil(remaining))
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_rate_limiter.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rate_limiter import SlidingWindowLimiter


class SlidingWindowLimiterTest(unittest.TestCase):
    def test_allows_up_to_limit_and_rejects_excess(self):
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=10.0)
        self.assertTrue(limiter.allow("k1", 100.0))
        self.assertTrue(limiter.allow("k1", 101.0))
        self.assertFalse(limiter.allow("k1", 102.0))

    def test_prunes_expired_entries_after_window(self):
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=5.0)
        self.assertTrue(limiter.allow("k1", 10.0))
        self.assertFalse(limiter.allow("k1", 14.9))
        self.assertTrue(limiter.allow("k1", 15.0))

    def test_retry_after_rounds_up_to_whole_seconds(self):
        limiter = SlidingWindowLimiter(max_requests=1, window_seconds=10.0)
        self.assertEqual(limiter.retry_after_seconds("k1", 100.0), 0)
        self.assertTrue(limiter.allow("k1", 100.0))
        self.assertEqual(limiter.retry_after_seconds("k1", 108.8), 2)
        self.assertEqual(limiter.retry_after_seconds("k1", 109.9), 1)
        self.assertEqual(limiter.retry_after_seconds("k1", 110.0), 0)

    def test_rejects_non_positive_config(self):
        with self.assertRaises(ValueError):
            SlidingWindowLimiter(max_requests=0, window_seconds=1.0)
        with self.assertRaises(ValueError):
            SlidingWindowLimiter(max_requests=1, window_seconds=0.0)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial sliding window rate limiter"
git -C repo rev-parse HEAD > program/base_sha.txt
