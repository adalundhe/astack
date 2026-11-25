#!/bin/bash
set -euo pipefail
mkdir -p program repo

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/retry_client.py <<'EOF'
from __future__ import annotations

from typing import Callable


def fetch_once(call: Callable[[], dict]) -> dict:
    return call()
EOF

git -C repo add retry_client.py
git -C repo commit -q -m "initial fetch_once helper"

git -C repo checkout -q -b lane/retry-client
cat > repo/retry_client.py <<'EOF'
from __future__ import annotations

import time
from typing import Callable

MAX_RETRIES = 7
POLL_SLEEP_SECONDS = 3.5


def fetch_with_retry(call: Callable[[], dict]) -> dict | None:
    """Poll until the upstream call succeeds."""
    for _ in range(MAX_RETRIES):
        try:
            result = call()
            if result.get("ready"):
                return result
            time.sleep(POLL_SLEEP_SECONDS)
        except Exception:
            return None
    return None
EOF

git -C repo add retry_client.py
git -C repo commit -q -m "Add fetch_with_retry polling helper"
git -C repo rev-parse HEAD > program/head_sha.txt
git -C repo diff main..lane/retry-client > program/change.diff
