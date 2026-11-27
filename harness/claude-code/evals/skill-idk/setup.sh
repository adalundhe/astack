#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home program/demo repo/src

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# rate-demo

Deterministic rate-limiter library comparing token-bucket and leaky-bucket traffic shaping in `src/limiter.py`.
EOF

cat > repo/src/limiter.py <<'EOF'
"""Deterministic token-bucket and leaky-bucket rate limiters."""
from __future__ import annotations


class TokenBucket:
    """Allows bursts up to `capacity`, refilling at `refill_rate` tokens/sec."""

    def __init__(self, capacity: float, refill_rate: float, now: float = 0.0) -> None:
        if capacity <= 0 or refill_rate <= 0:
            raise ValueError("capacity and refill_rate must be positive")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.tokens = float(capacity)
        self.last_ts = float(now)

    def allow(self, now: float, cost: float = 1.0) -> bool:
        if now < self.last_ts:
            raise ValueError("timestamps must be monotonic")
        elapsed = now - self.last_ts
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_ts = float(now)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class LeakyBucket:
    """Queues work up to `capacity` and drains at a fixed `leak_rate` units/sec."""

    def __init__(self, capacity: float, leak_rate: float, now: float = 0.0) -> None:
        if capacity <= 0 or leak_rate <= 0:
            raise ValueError("capacity and leak_rate must be positive")
        self.capacity = float(capacity)
        self.leak_rate = float(leak_rate)
        self.level = 0.0
        self.last_ts = float(now)

    def submit(self, now: float, units: float = 1.0) -> tuple[bool, float]:
        """Return (accepted, estimated_drain_delay_sec)."""
        if now < self.last_ts:
            raise ValueError("timestamps must be monotonic")
        elapsed = now - self.last_ts
        self.level = max(0.0, self.level - elapsed * self.leak_rate)
        self.last_ts = float(now)
        if self.level + units <= self.capacity:
            self.level += units
            delay = self.level / self.leak_rate
            return True, round(delay, 3)
        return False, -1.0
EOF

git -C repo add .
git -C repo commit -q -m "add deterministic TokenBucket and LeakyBucket limiters"
