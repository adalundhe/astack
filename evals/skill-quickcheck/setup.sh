#!/bin/bash
set -euo pipefail
mkdir -p program repo/docs repo/scripts repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Cache Service

## Tooling & runtime
- Run tests with `python3 -m unittest discover -s tests`.
- `scripts/run.sh` creates `./var/data` before launching the service, so `DATA_DIR` defaults to `./var/data`.
EOF

cat > repo/docs/ARCHITECTURE.md <<'EOF'
# Architecture Decisions

## AD-001: Single-threaded FIFO Cache
- `Cache` intentionally uses simple FIFO eviction (not LRU) to keep hot-path writes O(1) without pointer chasing.
- Upstream callers serialize access on a single event loop; adding mutexes or thread-safety locks is intentionally out of scope.
- **Expected contract:** updating an existing key via `put(key, value)` overwrites its value in place without growing the logical entry count or evicting live entries while distinct keys remain `<= capacity`.
EOF

cat > repo/scripts/run.sh <<'EOF'
#!/bin/sh
mkdir -p "${DATA_DIR:-./var/data}"
exec python3 -m src.cache
EOF
chmod +x repo/scripts/run.sh

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/cache.py <<'EOF'
from __future__ import annotations

import os
from collections import deque


class Cache:
    """Single-threaded FIFO cache (see docs/ARCHITECTURE.md AD-001)."""

    def __init__(self, capacity: int, data_dir: str | None = None) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.data_dir = data_dir or os.environ.get("DATA_DIR", "./var/data")
        self._data: dict[str, object] = {}
        self._order: deque[str] = deque()

    def get(self, key: str) -> object | None:
        return self._data.get(key)

    def put(self, key: str, value: object) -> None:
        if key not in self._data and len(self._data) >= self.capacity:
            oldest = self._order.popleft()
            self._data.pop(oldest, None)
        if key not in self._data:
            self._order.append(key)
        self._data[key] = value
EOF

cat > repo/tests/test_cache.py <<'EOF'
import unittest
from src.cache import Cache


class CacheTest(unittest.TestCase):
    def test_fifo_eviction(self) -> None:
        c = Cache(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("b"), 2)
        self.assertEqual(c.get("c"), 3)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial fifo cache"

cat > repo/src/cache.py <<'EOF'
from __future__ import annotations

import os
from collections import deque


class Cache:
    """Single-threaded FIFO cache (see docs/ARCHITECTURE.md AD-001)."""

    def __init__(self, capacity: int, data_dir: str | None = None) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.data_dir = data_dir or os.environ.get("DATA_DIR", "./var/data")
        self._data: dict[str, object] = {}
        self._order: deque[str] = deque()

    def get(self, key: str) -> object | None:
        return self._data.get(key)

    def put(self, key: str, value: object) -> None:
        self._order.append(key)
        self._data[key] = value
        if len(self._order) > self.capacity:
            oldest = self._order.popleft()
            self._data.pop(oldest, None)
EOF

git -C repo add .
git -C repo commit -q -m "simplify put path"
