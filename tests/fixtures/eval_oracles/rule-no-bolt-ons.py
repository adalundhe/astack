"""Separated offline oracle for `rule-no-bolt-ons`."""
from __future__ import annotations

from pathlib import Path

_FIXED_PRICING = '''from __future__ import annotations

_TIER_DISCOUNT_PCT: dict[str, int] = {
    "standard": 0,
    "pro": 10,
    "enterprise": 20,
    "nonprofit": 30,
}

_VOLUME_BREAKS: tuple[tuple[int, int], ...] = (
    (100, 15),
    (20, 10),
    (5, 5),
)

_MAX_DISCOUNT_PCT = 40


def _volume_discount_pct(qty: int) -> int:
    for min_qty, pct in _VOLUME_BREAKS:
        if qty >= min_qty:
            return pct
    return 0


def calculate_price(unit_price_cents: int, qty: int, tier: str = "standard") -> int:
    if unit_price_cents < 0:
        raise ValueError("unit_price_cents must be >= 0")
    if qty <= 0:
        raise ValueError("qty must be > 0")
    if tier not in _TIER_DISCOUNT_PCT:
        raise ValueError(f"unsupported tier: {tier!r}")
    discount_pct = min(_TIER_DISCOUNT_PCT[tier] + _volume_discount_pct(qty), _MAX_DISCOUNT_PCT)
    subtotal_cents = unit_price_cents * qty
    return subtotal_cents * (100 - discount_pct) // 100
'''

_FIXED_CHECKOUT = '''from __future__ import annotations

from pricing import calculate_price


def quote_order(items: list[tuple[int, int]], tier: str = "standard") -> dict[str, object]:
    subtotal_cents = sum(price * qty for price, qty in items)
    total_cents = sum(calculate_price(price, qty, tier=tier) for price, qty in items)
    return {
        "tier": tier,
        "subtotal_cents": subtotal_cents,
        "total_cents": total_cents,
    }
'''

_FIXED_TESTS = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from checkout import quote_order
from pricing import calculate_price


class PricingBaselineTest(unittest.TestCase):
    def test_standard_single_unit(self):
        self.assertEqual(calculate_price(1000, 1, tier="standard"), 1000)

    def test_pro_single_unit(self):
        self.assertEqual(calculate_price(1000, 1, tier="pro"), 900)

    def test_quote_order_basic(self):
        quote = quote_order([(1000, 1), (500, 2)], tier="pro")
        self.assertEqual(quote, {"tier": "pro", "subtotal_cents": 2000, "total_cents": 1800})

    def test_all_tiers_and_volume_breaks(self):
        self.assertEqual(calculate_price(1000, 1, tier="enterprise"), 800)
        self.assertEqual(calculate_price(1000, 1, tier="nonprofit"), 700)
        self.assertEqual(calculate_price(1000, 5, tier="standard"), 4750)
        self.assertEqual(calculate_price(1000, 20, tier="standard"), 18000)
        self.assertEqual(calculate_price(1000, 100, tier="standard"), 85000)
        self.assertEqual(calculate_price(1000, 20, tier="enterprise"), 14000)

    def test_combined_discount_capped_at_40_percent(self):
        self.assertEqual(calculate_price(1000, 100, tier="nonprofit"), 60000)

    def test_quote_order_with_enterprise_volume_lines(self):
        quote = quote_order([(1000, 10), (500, 20)], tier="enterprise")
        self.assertEqual(quote, {"tier": "enterprise", "subtotal_cents": 20000, "total_cents": 14500})

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            calculate_price(1000, 1, tier="unknown")
        with self.assertRaises(ValueError):
            calculate_price(1000, 0, tier="standard")
        with self.assertRaises(ValueError):
            calculate_price(-1, 2, tier="pro")


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "pricing.py").write_text(_FIXED_PRICING, encoding="utf-8")
    (repo / "src" / "checkout.py").write_text(_FIXED_CHECKOUT, encoding="utf-8")
    (repo / "tests" / "test_pricing.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Unified src/pricing.py and src/checkout.py into a single table-driven pricing model "
            "supporting all four tiers, volume breaks, and the 40% discount cap; deleted calculate_price_v2 "
            "and mode-switch boolean flags; added unit tests for all tiers, breaks, cap, and validation."
        ),
    }
