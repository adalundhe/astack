#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Money & Tax Utilities

## `src/money.py`

Implement `format_cents(cents: int) -> str`:
- Format integer cents as a US dollar string with two decimal places and no thousands separators:
  - `format_cents(0) == "$0.00"`
  - `format_cents(5) == "$0.05"`
  - `format_cents(1234) == "$12.34"`
  - `format_cents(-250) == "-$2.50"`
  - `format_cents(100000) == "$1000.00"`
- Raise `TypeError` for `bool` or non-`int` inputs.

## Tests

Run `python3 -B -m unittest discover -s tests`.
EOF

cat > repo/src/money.py <<'EOF'
"""Currency parsing and formatting helpers."""
from __future__ import annotations


def parse_dollars_to_cents(amount: str) -> int:
    """Parse a non-negative dollar string such as '12.34' into integer cents."""
    dollars_str, _, cents_str = amount.strip().partition(".")
    cents_str = (cents_str + "00")[:2]
    return int(dollars_str) * 100 + int(cents_str)
EOF

cat > repo/tests/test_money.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from money import parse_dollars_to_cents


class MoneyTest(unittest.TestCase):
    def test_parse_dollars_to_cents(self):
        self.assertEqual(parse_dollars_to_cents("12.34"), 1234)
        self.assertEqual(parse_dollars_to_cents("0.05"), 5)
EOF

cat > repo/src/tax.py <<'EOF'
"""Sales tax calculation helpers."""
from __future__ import annotations


def compute_tax_cents(subtotal_cents: int, rate_bps: int) -> int:
    """Compute tax in cents from subtotal_cents and rate in basis points (100 bps = 1%).

    Rounds half up to the nearest cent.
    """
    if subtotal_cents < 0 or rate_bps < 0:
        raise ValueError("subtotal_cents and rate_bps must be non-negative")
    return (subtotal_cents * rate_bps + 500) // 1000
EOF

cat > repo/tests/test_tax.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tax import compute_tax_cents


class TaxTest(unittest.TestCase):
    def test_eight_percent_tax(self):
        self.assertEqual(compute_tax_cents(10000, 800), 800)

    def test_rounds_half_up(self):
        self.assertEqual(compute_tax_cents(100, 725), 7)
        self.assertEqual(compute_tax_cents(1000, 725), 73)
EOF

git -C repo add .
git -C repo commit -q -m "initial money and tax modules"
git -C repo rev-parse HEAD > program/base_sha.txt
git -C repo checkout -q -b feat/format-cents
