#!/bin/bash
set -euo pipefail
mkdir -p program repo-lib/src repo-lib/tests repo-app/src repo-app/tests

git -C repo-lib init -q -b main
git -C repo-lib config user.name eval
git -C repo-lib config user.email eval@example.invalid
git -C repo-lib config commit.gpgsign false

cat > repo-lib/src/pricing_lib.py <<'EOF'
"""Shared pricing library."""
from __future__ import annotations


def calculate_total_cents(subtotal_cents: int) -> int:
    return subtotal_cents
EOF

cat > repo-lib/tests/test_pricing_lib.py <<'EOF'
import unittest
from src.pricing_lib import calculate_total_cents


class PricingLibTest(unittest.TestCase):
    def test_subtotal(self):
        self.assertEqual(calculate_total_cents(1000), 1000)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo-lib add .
git -C repo-lib commit -q -m "initial pricing library v1"

cat > repo-lib/src/pricing_lib.py <<'EOF'
"""Shared pricing library."""
from __future__ import annotations


def calculate_total_cents(subtotal_cents: int, tax_rate_bps: int = 0) -> int:
    tax = (subtotal_cents * tax_rate_bps) // 10_000
    return subtotal_cents + tax
EOF

cat > repo-lib/tests/test_pricing_lib.py <<'EOF'
import unittest
from src.pricing_lib import calculate_total_cents


class PricingLibTest(unittest.TestCase):
    def test_subtotal_with_tax_bps(self):
        self.assertEqual(calculate_total_cents(1000, tax_rate_bps=825), 1082)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo-lib add .
git -C repo-lib commit -q -m "feat: add backward-compatible tax_rate_bps parameter"

git -C repo-app init -q -b main
git -C repo-app config user.name eval
git -C repo-app config user.email eval@example.invalid
git -C repo-app config commit.gpgsign false

cat > repo-app/dependencies.json <<'EOF'
{
  "service": "checkout-app",
  "depends_on": [
    {
      "repo": "repo-lib",
      "package": "pricing_lib",
      "requires_feature": "calculate_total_cents(subtotal_cents, tax_rate_bps=...)"
    }
  ]
}
EOF

cat > repo-app/src/checkout.py <<'EOF'
"""Checkout service consuming pricing_lib from repo-lib."""
from __future__ import annotations


def quote_order_cents(subtotal_cents: int, tax_rate_bps: int, pricing_mod) -> int:
    return pricing_mod.calculate_total_cents(subtotal_cents, tax_rate_bps=tax_rate_bps)
EOF

cat > repo-app/tests/test_checkout.py <<'EOF'
import unittest
from src.checkout import quote_order_cents


class _StubPricing:
    @staticmethod
    def calculate_total_cents(subtotal_cents: int, tax_rate_bps: int = 0) -> int:
        return subtotal_cents + (subtotal_cents * tax_rate_bps) // 10_000


class CheckoutTest(unittest.TestCase):
    def test_quote_order(self):
        self.assertEqual(quote_order_cents(2000, 500, _StubPricing), 2100)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo-app add .
git -C repo-app commit -q -m "feat: pass tax_rate_bps to repo-lib calculate_total_cents"

cat > program/release-plan.json <<'EOF'
{
  "name": "pricing-tax-rollout",
  "goal": "Roll out tax_rate_bps support in pricing_lib and checkout-app without breaking live callers.",
  "steps": [
    {
      "id": "deploy-app",
      "repo": "repo-app",
      "ref": "latest",
      "depends_on": [],
      "verify_cmd": "python3 -m unittest discover -s tests",
      "rollback_note": "Rollback repo-app to previous version"
    },
    {
      "id": "release-lib",
      "repo": "repo-lib",
      "ref": "main",
      "depends_on": ["deploy-app"],
      "verify_cmd": "python3 -m unittest discover -s tests",
      "rollback_note": "Rollback repo-lib to previous version"
    }
  ]
}
EOF
