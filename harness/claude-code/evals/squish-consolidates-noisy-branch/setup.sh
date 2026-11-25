#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Alice"
git -C repo config user.email "alice@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/retry.py <<'EOF'
def backoff(attempt: int) -> float:
    return float(2 ** attempt)
EOF
cat > repo/tests/test_retry.py <<'EOF'
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retry import backoff

class RetryTest(unittest.TestCase):
    def test_backoff(self):
        self.assertGreaterEqual(backoff(1), 1.0)
EOF
git -C repo add .
git -C repo commit -q -m "initial retry helper"
git -C repo rev-parse HEAD > program/base_sha.txt

git -C repo checkout -q -b feat/retry-jitter

cat > repo/src/retry.py <<'EOF'
def backoff(attempt: int, cap: float = 30.0) -> float:
    return min(cap, float(2 ** attempt))
EOF
git -C repo commit -q -am "wip cap"

cat > repo/src/retry.py <<'EOF'
def backoff(attempt: int, cap: float = 30.0) -> float:
    return min(cap, float(2 ** max(0, attempt)))
EOF
git -C repo commit -q -am "fixup negative attempt"

cat > repo/src/retry.py <<'EOF'
def backoff(attempt: int, cap: float = 30.0, jitter: float = 0.0) -> float:
    base = min(cap, float(2 ** max(0, attempt)))
    return max(0.0, base + jitter)
EOF
GIT_AUTHOR_NAME="Bob" GIT_AUTHOR_EMAIL="bob@example.invalid" git -C repo commit -q -am "add jitter arg"

cat > repo/tests/test_retry.py <<'EOF'
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retry import backoff

class RetryTest(unittest.TestCase):
    def test_backoff_cap_and_jitter(self):
        self.assertEqual(backoff(10, cap=30.0), 30.0)
        self.assertEqual(backoff(1, cap=30.0, jitter=0.5), 2.5)
EOF
git -C repo commit -q -am "add test"

echo "# tmp" >> repo/src/retry.py
git -C repo commit -q -am "oops temp comment"

sed -i.bak '/^# tmp$/d' repo/src/retry.py && rm -f repo/src/retry.py.bak
git -C repo commit -q -am "remove oops comment"

git -C repo rev-parse HEAD > program/pre_squish_sha.txt
git -C repo rev-parse HEAD^{tree} > program/pre_squish_tree.txt
