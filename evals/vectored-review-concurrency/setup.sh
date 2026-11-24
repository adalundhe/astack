#!/bin/bash
set -euo pipefail
mkdir -p program repo
if [ -n "${ASTACK_EVAL_SETTINGS_JSON:-}" ]; then
  printf '%s\n' "$ASTACK_EVAL_SETTINGS_JSON" > program/settings.json
else
cat > program/settings.json <<'EOF'
{
  "roles": {
    "worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  },
  "reviewer_pool": [
    {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
    {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  ]
}
EOF
fi

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false
cat > repo/pool.py <<'EOF'
import threading


class JobPool:
    def __init__(self):
        self._lock = threading.Lock()
        self._items = []

    def push(self, item):
        with self._lock:
            self._items.append(item)

    def pop(self):
        with self._lock:
            return self._items.pop(0) if self._items else None
EOF
git -C repo add pool.py
git -C repo commit -q -m "initial job pool"

git -C repo checkout -q -b lane/concurrent-batch
cat > repo/pool.py <<'EOF'
import threading


class JobPool:
    def __init__(self):
        self._lock = threading.Lock()
        self._items = []
        self.drained = 0

    def push(self, item):
        with self._lock:
            self._items.append(item)

    def pop(self):
        with self._lock:
            return self._items.pop(0) if self._items else None

    def drain_batch(self, limit):
        if limit <= 0:
            return []
        with self._lock:
            batch = list(self._items[:limit])
        with self._lock:
            del self._items[: len(batch)]
            self.drained += len(batch)
        return batch
EOF
git -C repo add pool.py
git -C repo commit -q -m "add concurrent drain_batch with stats counter"
git -C repo diff main..lane/concurrent-batch > program/change.diff
mkdir -p program/base
git -C repo show main:pool.py > program/base/pool.py
