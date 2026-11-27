"""Separated offline oracle for `rule-tests-assert-behaviour`."""
from __future__ import annotations

from pathlib import Path

FIXED_CHECKOUT = r'''"""Checkout pricing service."""
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
            return max(0, subtotal_cents - 500)
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
        tax = self._compute_tax(discounted, tax_rate_bps)
        return discounted + tax
'''

FIXED_TESTS = r'''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from checkout import CheckoutService, LineItem


class CheckoutBehaviorTest(unittest.TestCase):
    def setUp(self):
        self.svc = CheckoutService()

    def test_total_without_coupon(self):
        total = self.svc.calculate_total(
            [LineItem("book", 1250, 2), LineItem("pen", 500, 1)],
            tax_rate_bps=800,
        )
        self.assertEqual(total, 3240)

    def test_save20_taxes_post_discount_subtotal(self):
        total = self.svc.calculate_total(
            [LineItem("jacket", 1000, 1)],
            tax_rate_bps=1000,
            coupon_code="SAVE20",
        )
        self.assertEqual(total, 880)

    def test_flat500_applies_discount_and_floors_at_zero(self):
        normal = self.svc.calculate_total(
            [LineItem("lamp", 1500, 1)],
            tax_rate_bps=1000,
            coupon_code="FLAT500",
        )
        floored = self.svc.calculate_total(
            [LineItem("mug", 300, 1)],
            tax_rate_bps=1000,
            coupon_code="FLAT500",
        )
        self.assertEqual(normal, 1100)
        self.assertEqual(floored, 0)

    def test_empty_cart_costs_zero(self):
        self.assertEqual(self.svc.calculate_total([], tax_rate_bps=800), 0)

    def test_rejects_invalid_coupon_items_and_tax_rate(self):
        with self.assertRaises(ValueError):
            self.svc.calculate_total([LineItem("mug", 500, 1)], tax_rate_bps=800, coupon_code="UNKNOWN")
        with self.assertRaises(ValueError):
            self.svc.calculate_total([LineItem("mug", -1, 1)], tax_rate_bps=800)
        with self.assertRaises(ValueError):
            self.svc.calculate_total([LineItem("mug", 500, 0)], tax_rate_bps=800)
        with self.assertRaises(ValueError):
            self.svc.calculate_total([LineItem("mug", 500, 1)], tax_rate_bps=-50)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    """Fix checkout pricing bugs and replace mock-coupled tests with behavior tests."""
    repo = ws / "repo"
    (repo / "src" / "checkout.py").write_text(FIXED_CHECKOUT, encoding="utf-8")
    (repo / "tests" / "test_checkout.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Fixed post-discount tax calculation and FLAT500 zero-floor clamping in src/checkout.py. "
            "Replaced mock-coupled, tautological, and sleep-based tests in tests/test_checkout.py "
            "with fast behavior tests using hand-worked expected totals and typed ValueError checks."
        ),
    }
