"""Separated offline oracle for `rule-comment-cop`."""
from __future__ import annotations

from pathlib import Path

CLEAN_SOURCE = '''# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Acme Telemetry Inc. All rights reserved.
"""Sliding-window rate limiter for inbound API keys."""
from __future__ import annotations

from collections import deque
import math


class SlidingWindowLimiter:
    """Limits requests per key within a rolling window."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = max_requests
        self.window_seconds = float(window_seconds)
        self._buckets: dict[str, deque[float]] = {}
        self._allowed_count = 0

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._buckets.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        return bucket

    def allow(self, key: str, now: float) -> bool:
        """Record a request at `now` and return True if within the limit."""
        bucket = self._prune(key, now)
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        self._allowed_count += 1
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
'''


def apply(ws: Path) -> dict[str, object]:
    """Strip narrating/stale/commented-out comments while keeping license and RFC constraint."""
    (ws / "repo" / "src" / "rate_limiter.py").write_text(CLEAN_SOURCE, encoding="utf-8")
    return {
        "final_text": (
            "Removed narrating comments, ASCII banners, OPS-991 history note, and commented-out code "
            "from src/rate_limiter.py while preserving the SPDX/Copyright header and the RFC 6585 / "
            "Envoy Retry-After constraint comment. All unit tests pass."
        ),
    }
