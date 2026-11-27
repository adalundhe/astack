#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Checkout Pricing Service

Computes order totals in integer cents.

## Rules
- `LineItem(sku, unit_price_cents, quantity)`: `unit_price_cents` must be `>= 0` and `quantity` must be `>= 1`; otherwise raise `ValueError`.
- `tax_rate_bps` (basis points, e.g. `800` = 8%) must be `>= 0`; otherwise raise `ValueError`.
- `subtotal = sum(item.unit_price_cents * item.quantity for item in items)`.
- Coupons:
  - `None` or `""`: no discount.
  - `"SAVE20"`: 20% off subtotal (`discounted = subtotal - (subtotal * 20 // 100)`).
  - `"FLAT500"`: 500 cents off subtotal, floored at `0` (never negative).
  - Any other coupon string raises `ValueError`.
- Tax is computed on the **post-discount** subtotal: `tax = discounted * tax_rate_bps // 10_000`.
- `total = discounted + tax`.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/checkout.py <<'EOF'
"""Checkout pricing service."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price_cents: int
    quantity: int


class CheckoutService:
    def _compute_subtotal(self, items: list[LineItem]) -> int:
        subtotal = 0
        for item in items:
            if item.unit_price_cents < 0 or item.quantity <= 0:
                raise ValueError(f"invalid line item: {item}")
            subtotal += item.unit_price_cents * item.quantity
        return subtotal

    def _apply_discount(self, subtotal_cents: int, coupon_code: str | None) -> int:
        if not coupon_code:
            return subtotal_cents
        if coupon_code == "SAVE20":
            return subtotal_cents - (subtotal_cents * 20 // 100)
        if coupon_code == "FLAT500":
            # BUG: missing max(0, ...) floor allows negative totals when subtotal < 500
            return subtotal_cents - 500
        raise ValueError(f"unknown coupon: {coupon_code}")

    def _compute_tax(self, taxable_cents: int, tax_rate_bps: int) -> int:
        if tax_rate_bps < 0:
            raise ValueError("tax_rate_bps must be non-negative")
        return taxable_cents * tax_rate_bps // 10_000

    def calculate_total(
        self,
        items: list[LineItem],
        tax_rate_bps: int,
        coupon_code: str | None = None,
    ) -> int:
        subtotal = self._compute_subtotal(items)
        discounted = self._apply_discount(subtotal, coupon_code)
        # BUG: computes tax on pre-discount subtotal instead of discounted amount
        tax = self._compute_tax(subtotal, tax_rate_bps)
        return discounted + tax
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_checkout.py <<'EOF'
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from checkout import CheckoutService, LineItem


class CheckoutMockCoupledTest(unittest.TestCase):
    def test_calls_internal_helpers_with_mocks(self):
        svc = CheckoutService()
        items = [LineItem("sku-1", 1000, 1)]
        with (
            patch.object(svc, "_apply_discount", return_value=800) as m_disc,
            patch.object(svc, "_compute_tax", return_value=80) as m_tax,
        ):
            total = svc.calculate_total(items, tax_rate_bps=1000, coupon_code="SAVE20")
            self.assertEqual(total, 880)
            m_disc.assert_called_once()
            m_tax.assert_called_once()

    def test_tautological_calculation(self):
        svc = CheckoutService()
        items = [LineItem("sku-2", 500, 2)]
        expected = svc._apply_discount(svc._compute_subtotal(items), None) + svc._compute_tax(1000, 800)
        self.assertEqual(svc.calculate_total(items, tax_rate_bps=800), expected)

    def test_checkout_latency_with_sleep(self):
        svc = CheckoutService()
        start = time.monotonic()
        time.sleep(0.5)
        total = svc.calculate_total([LineItem("sku-3", 1000, 1)], tax_rate_bps=0)
        elapsed = time.monotonic() - start
        self.assertEqual(total, 1000)
        self.assertLess(elapsed, 2.0)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial checkout service with mock-coupled tests"
git -C repo rev-parse HEAD > program/base_sha.txt
