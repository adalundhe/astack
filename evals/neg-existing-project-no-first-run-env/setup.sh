#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests program/astack_home/repo/docs

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > program/astack_home/repo/docs/environment.md <<'EOF'
# repo Environment Notes

SENTINEL_EXISTING_ENV_V1: established 2026-10-01.
- Python 3.12 and git are ready.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/calc.py <<'EOF'
from __future__ import annotations


def discount_price(cents: int, percent: int) -> int:
    """Apply an integer percentage discount (0..100) and return discounted cents."""
    if cents < 0:
        raise ValueError("cents must be non-negative")
    if not (0 <= percent <= 100):
        raise ValueError("percent must be between 0 and 100")
    return cents + (cents * percent) // 100
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_calc.py <<'EOF'
import unittest

from src.calc import discount_price


class CalcTest(unittest.TestCase):
    def test_discount_subtracts_percentage(self):
        self.assertEqual(discount_price(1000, 20), 800)
        self.assertEqual(discount_price(1000, 0), 1000)
        self.assertEqual(discount_price(1000, 100), 0)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            discount_price(-1, 10)
        with self.assertRaises(ValueError):
            discount_price(100, 101)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
