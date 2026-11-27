#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/cache.py <<'EOF'
"""In-process TTL + bounded LRU cache (contains planted eviction, bound, and clock bugs)."""
from __future__ import annotations

import time
from typing import Any


class TTLCache:
    def __init__(self, max_entries: int = 128, default_ttl_seconds: float = 60.0) -> None:
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self._data: dict[str, tuple[Any, float]] = {}

    def put(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        # Bug 1: uses wall-clock time.time() instead of time.monotonic()
        expires_at = time.time() + ttl
        # Bug 2: never enforces max_entries bound on insertion
        self._data[key] = (value, expires_at)

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._data.get(key)
        if entry is None:
            return default
        value, expires_at = entry
        if time.time() >= expires_at:
            del self._data[key]
            return default
        # Bug 3: never updates LRU recency order on read
        return value

    def evict_one(self) -> str | None:
        if not self._data:
            return None
        # Bug 4: dict.popitem() removes the MOST recently inserted item (LIFO) instead of LRU oldest
        key, _ = self._data.popitem()
        return key

    def __len__(self) -> int:
        # Bug 5: counts already-expired entries
        return len(self._data)
EOF

cat > repo/tests/test_cache.py <<'EOF'
import unittest
from src.cache import TTLCache


class CacheSmokeTest(unittest.TestCase):
    def test_put_and_get(self):
        c = TTLCache(max_entries=4, default_ttl_seconds=10.0)
        c.put("a", 1)
        self.assertEqual(c.get("a"), 1)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial cache with eviction and size-bound bugs"

cat > program/brief.md <<'EOF'
# Task Brief

Make the cache better.
EOF
