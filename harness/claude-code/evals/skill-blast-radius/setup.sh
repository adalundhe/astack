#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/pricing.py <<'EOF'
"""Order pricing helpers."""
from __future__ import annotations


def total_cents(items: list[dict[str, int]], tax_bps: int = 0) -> int:
    """Return integer total in cents including half-up tax."""
    subtotal = sum(item["qty"] * item["unit_cents"] for item in items)
    tax = (subtotal * tax_bps + 5000) // 10000
    return subtotal + tax


def quote_amount(items: list[dict[str, int]], tax_bps: int = 0) -> int:
    """Delegate order quote computation to total_cents."""
    return total_cents(items, tax_bps)
EOF

cat > repo/src/invoices.py <<'EOF'
"""Customer invoice batch accumulator."""
from __future__ import annotations

from src.pricing import total_cents as compute_order_total


def build_invoice_batch_total(orders: list[dict[str, object]]) -> int:
    """Sum integer totals across a batch of customer orders."""
    running_total = 0
    for order in orders:
        items = order["items"]
        tax_bps = int(order.get("tax_bps", 0))
        amount = compute_order_total(items, tax_bps)
        running_total += amount
    return running_total
EOF

cat > repo/src/exports.py <<'EOF'
"""CSV export formatter for finance reconciliation."""
from __future__ import annotations

from src.pricing import quote_amount


def format_export_row(order_id: str, items: list[dict[str, int]], tax_bps: int) -> str:
    """Format an order row with dollar total for accounting CSV export."""
    cents = quote_amount(items, tax_bps)
    dollars = f"{cents / 100:.2f}"
    return f"{order_id},{dollars}"
EOF

cat > repo/src/webhooks.py <<'EOF'
"""Outbound webhook payload builder with dynamic metric registry."""
from __future__ import annotations

from src import pricing

CALCULATOR_REGISTRY: dict[str, str] = {
    "invoice.created": "total_cents",
}


def build_webhook_payload(
    event_type: str,
    items: list[dict[str, int]],
    tax_bps: int,
    high_value_threshold_cents: int = 10000,
) -> dict[str, object]:
    """Build outbound JSON payload using dynamic calculator lookup."""
    fn_name = CALCULATOR_REGISTRY[event_type]
    calculator = getattr(pricing, fn_name)
    amount = calculator(items, tax_bps)
    return {
        "event": event_type,
        "amount_cents": amount,
        "high_value": amount >= high_value_threshold_cents,
    }
EOF

cat > repo/tests/test_pricing.py <<'EOF'
import unittest
from src.exports import format_export_row
from src.invoices import build_invoice_batch_total
from src.pricing import total_cents
from src.webhooks import build_webhook_payload


class PricingBlastRadiusBaselineTest(unittest.TestCase):
    def test_total_cents_and_consumers(self):
        items = [{"qty": 2, "unit_cents": 2500}]
        self.assertEqual(total_cents(items, 800), 5400)
        self.assertEqual(build_invoice_batch_total([{"items": items, "tax_bps": 800}]), 5400)
        self.assertEqual(format_export_row("ord-1", items, 800), "ord-1,54.00")
        payload = build_webhook_payload("invoice.created", items, 800)
        self.assertEqual(payload["amount_cents"], 5400)
        self.assertFalse(payload["high_value"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial pricing and downstream consumers"

cat > program/proposed_change.patch <<'EOF'
Author note: Only `src/pricing.py` and `tests/test_pricing.py` show up when grepping `total_cents(`,
so changing `total_cents` to return a breakdown dict is safe for the rest of the codebase.

--- a/src/pricing.py
+++ b/src/pricing.py
@@ -2,9 +2,9 @@
 from __future__ import annotations
 
 
-def total_cents(items: list[dict[str, int]], tax_bps: int = 0) -> int:
-    """Return integer total in cents including half-up tax."""
+def total_cents(items: list[dict[str, int]], tax_bps: int = 0) -> dict[str, int]:
+    """Return breakdown dictionary with subtotal, tax, and total in cents."""
     subtotal = sum(item["qty"] * item["unit_cents"] for item in items)
     tax = (subtotal * tax_bps + 5000) // 10000
-    return subtotal + tax
+    return {"subtotal_cents": subtotal, "tax_cents": tax, "total_cents": subtotal + tax}
EOF
