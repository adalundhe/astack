#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Order Pricing Engine

Provides `calculate_price` in `src/pricing.py` and `quote_order` in `src/checkout.py`.

## Pricing Rules
- Supported tiers and base discounts:
  - `standard`: 0%
  - `pro`: 10%
  - `enterprise`: 20%
  - `nonprofit`: 30%
- Volume discounts (added to tier discount):
  - `qty >= 100`: +15%
  - `qty >= 20`: +10%
  - `qty >= 5`: +5%
  - `qty < 5`: +0%
- Combined discount cap: `total_discount_pct = min(tier_pct + volume_pct, 40)`.
- Line total: `subtotal_cents = unit_price_cents * qty`; `final_cents = subtotal_cents * (100 - total_discount_pct) // 100`.
- Validation: unknown `tier`, `unit_price_cents < 0`, or `qty <= 0` raises `ValueError`.

## Public API
- `src/pricing.py`:
  - `calculate_price(unit_price_cents: int, qty: int, tier: str = "standard") -> int`
- `src/checkout.py`:
  - `quote_order(items: list[tuple[int, int]], tier: str = "standard") -> dict`
    Returns `{"tier": tier, "subtotal_cents": int, "total_cents": int}` where each `(unit_price_cents, qty)` line is priced via `calculate_price`.
- Remove legacy `calculate_price_v2` copies and boolean mode-switch parameters (`use_new_mode`, `enterprise_override`, etc.).
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/pricing.py <<'EOF'
from __future__ import annotations


def calculate_price(
    unit_price_cents: int,
    qty: int,
    tier: str = "standard",
    use_new_mode: bool = False,
    enterprise_override: bool = False,
) -> int:
    if use_new_mode:
        return calculate_price_v2(unit_price_cents, qty, tier=tier, enterprise_override=enterprise_override)
    if unit_price_cents < 0 or qty <= 0:
        raise ValueError("invalid price or quantity")
    subtotal = unit_price_cents * qty
    if tier == "standard":
        return subtotal
    if tier == "pro":
        return subtotal * 90 // 100
    raise ValueError(f"unsupported tier: {tier}")


def calculate_price_v2(
    unit_price_cents: int,
    qty: int,
    tier: str = "standard",
    enterprise_override: bool = False,
) -> int:
    """Partial second copy added during an earlier migration."""
    if unit_price_cents < 0 or qty <= 0:
        raise ValueError("invalid price or quantity")
    subtotal = unit_price_cents * qty
    if enterprise_override or tier == "enterprise":
        return subtotal * 80 // 100
    if tier == "pro":
        return subtotal * 90 // 100
    return subtotal
EOF

cat > repo/src/checkout.py <<'EOF'
from __future__ import annotations

from pricing import calculate_price, calculate_price_v2


def quote_order(
    items: list[tuple[int, int]],
    tier: str = "standard",
    use_new_mode: bool = False,
    enterprise_override: bool = False,
) -> dict[str, object]:
    subtotal = sum(price * qty for price, qty in items)
    if use_new_mode:
        total = sum(
            calculate_price_v2(price, qty, tier=tier, enterprise_override=enterprise_override)
            for price, qty in items
        )
    else:
        total = sum(
            calculate_price(price, qty, tier=tier, use_new_mode=False, enterprise_override=False)
            for price, qty in items
        )
    return {
        "tier": tier,
        "subtotal_cents": subtotal,
        "total_cents": total,
    }
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_pricing.py <<'EOF'
import sys
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


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial pricing scaffold with v2 and mode flags"
