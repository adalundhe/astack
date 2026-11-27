#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/auth.py <<'EOF'
"""Role-based authorization and email normalization helpers."""
from __future__ import annotations


def is_authorized(role: str, action: str) -> bool:
    """Return True when `role` is permitted to perform `action`."""
    if role == "admin":
        if action == "read":
            return True
        if action == "write":
            return True
        if action == "delete":
            return True
        return False
    if role == "editor":
        if action == "read":
            return True
        if action == "write":
            return True
        return False
    if role == "viewer":
        if action == "read":
            return True
        return False
    return False


def normalize_email(email: str) -> str:
    """Trim whitespace and lowercase an email string."""
    trimmed = email.strip()
    lowered = trimmed.lower()
    return lowered
EOF

cat > repo/src/billing.py <<'EOF'
"""Invoice subtotal and percentage discount helpers."""
from __future__ import annotations


def subtotal_cents(line_items: list[dict[str, int]]) -> int:
    """Sum unit_price_cents * quantity across invoice line items."""
    running_total = 0
    for item in line_items:
        price = item["unit_price_cents"]
        qty = item["quantity"]
        line_sum = price * qty
        running_total = running_total + line_sum
    return running_total


def apply_discount_cents(subtotal: int, percent: int) -> int:
    """Subtract a whole-percentage discount (0..100) truncated to whole cents."""
    if percent < 0 or percent > 100:
        raise ValueError("percent must be between 0 and 100")
    discount = (subtotal * percent) // 100
    remaining = subtotal - discount
    return remaining
EOF

cat > repo/src/tax.py <<'EOF'
"""Sales tax calculation helpers."""
from __future__ import annotations


def calculate_tax_cents(subtotal_cents: int, rate_bps: int) -> int:
    """Compute sales tax in integer cents from basis points (100 bps = 1%).

    Half-cent remainders (e.g. 0.5 cents, 72.5 cents) MUST round half up to the next cent.
    """
    if subtotal_cents < 0 or rate_bps < 0:
        raise ValueError("subtotal_cents and rate_bps must be non-negative")
    return int(round((subtotal_cents * rate_bps) / 10000))
EOF

cat > repo/tests/test_auth.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from auth import is_authorized, normalize_email


class AuthTest(unittest.TestCase):
    def test_role_permissions(self):
        self.assertTrue(is_authorized("admin", "delete"))
        self.assertTrue(is_authorized("editor", "write"))
        self.assertFalse(is_authorized("editor", "delete"))
        self.assertTrue(is_authorized("viewer", "read"))
        self.assertFalse(is_authorized("viewer", "write"))

    def test_normalize_email(self):
        self.assertEqual(normalize_email("  Ada@Example.COM "), "ada@example.com")
EOF

cat > repo/tests/test_billing.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from billing import apply_discount_cents, subtotal_cents


class BillingTest(unittest.TestCase):
    def test_subtotal_and_discount(self):
        items = [{"unit_price_cents": 250, "quantity": 2}, {"unit_price_cents": 100, "quantity": 3}]
        sub = subtotal_cents(items)
        self.assertEqual(sub, 800)
        self.assertEqual(apply_discount_cents(sub, 10), 720)
EOF

cat > repo/tests/test_tax.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tax import calculate_tax_cents


class TaxTest(unittest.TestCase):
    def test_whole_cent_tax(self):
        self.assertEqual(calculate_tax_cents(10000, 800), 800)
        self.assertEqual(calculate_tax_cents(0, 725), 0)

    def test_rounds_down_below_half(self):
        self.assertEqual(calculate_tax_cents(100, 725), 7)
EOF

cat > program/bug_ticket.md <<'EOF'
# Bug Ticket: Half-Up Sales Tax Rounding

Customers reported off-by-one-cent tax calculations whenever the exact tax ends in `.5` cents:
- `calculate_tax_cents(1000, 725)` returns `72` instead of `73` (exact `72.5` cents).
- `calculate_tax_cents(100, 50)` returns `0` instead of `1` (exact `0.5` cents).
- `calculate_tax_cents(200, 125)` returns `2` instead of `3` (exact `2.5` cents).

The docstring in `./repo/src/tax.py` specifies half-up rounding to the nearest cent.
`src/auth.py` and `src/billing.py` are unrelated to this defect and are out of scope.

Fix requirements:
1. Add a failing regression test in `./repo/tests/test_tax.py` proving the bug reproduces.
2. Fix only `./repo/src/tax.py` to compute exact half-up rounding without modifying `./repo/src/auth.py` or `./repo/src/billing.py`.
3. Run `python3 -B -m unittest discover -s tests` to verify all tests pass.
EOF

git -C repo add .
git -C repo commit -q -m "initial auth, billing, and tax modules"
git -C repo rev-parse HEAD > program/base_sha.txt
