#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests program

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/greeting.py <<'EOF'
from __future__ import annotations


def format_greeting(name: str) -> str:
    """Return a standard greeting for `name`."""
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name must not be empty")
    return f"Helo, {cleaned}!"
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_greeting.py <<'EOF'
import unittest

from src.greeting import format_greeting


class GreetingTest(unittest.TestCase):
    def test_formats_standard_greeting(self):
        self.assertEqual(format_greeting("Ada"), "Hello, Ada!")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
