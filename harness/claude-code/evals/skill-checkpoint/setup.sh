#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/billing.py <<'EOF'
"""Billing invoice helpers."""
from __future__ import annotations


def empty_invoice() -> list[dict]:
    return []
EOF

cat > repo/tests/test_billing.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from billing import empty_invoice


class BillingTest(unittest.TestCase):
    def test_empty_invoice(self):
        self.assertEqual(empty_invoice(), [])
EOF

git -C repo add .
git -C repo commit -q -m "initial billing skeleton"

git -C repo checkout -q -b lane/billing

cat > repo/src/billing.py <<'EOF'
"""Billing invoice helpers."""
from __future__ import annotations


def empty_invoice() -> list[dict]:
    return []


def add_line_item(items: list[dict], sku: str, unit_cents: int, qty: int) -> int:
    """Append a line item and return the updated invoice subtotal in cents."""
    if unit_cents < 0 or qty < 1:
        raise ValueError("unit_cents must be >= 0 and qty must be >= 1")
    items.append({"sku": sku, "unit_cents": unit_cents, "qty": qty})
    return sum(entry["unit_cents"] * entry["qty"] for entry in items)
EOF

cat > repo/tests/test_billing.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from billing import add_line_item, empty_invoice


class BillingTest(unittest.TestCase):
    def test_empty_invoice(self):
        self.assertEqual(empty_invoice(), [])

    def test_add_line_item_subtotal(self):
        items = empty_invoice()
        self.assertEqual(add_line_item(items, "PRO", 1500, 2), 3000)
        self.assertEqual(add_line_item(items, "ADDON", 500, 1), 3500)
EOF

git -C repo commit -q -am "step 1: implement add_line_item subtotal calculation"
STEP1_SHA=$(git -C repo rev-parse HEAD)
echo "${STEP1_SHA}" > program/step1_sha.txt

cat > program/settings.json <<'EOF'
{
  "automation": {
    "mode": "agentic-only"
  }
}
EOF

cat > program/LANES.md <<EOF
<!-- astack lane log -->
# Billing Program

Repository: ./repo
Verification command: \`python3 -B -m unittest discover -s tests\`

## Plan
- Step 1 (completed at ${STEP1_SHA}): implement \`add_line_item\` subtotal calculation in \`src/billing.py\` with unit tests in \`tests/test_billing.py\`.
- Step 2 (remaining): implement \`apply_discount(subtotal_cents, pct)\` in \`src/billing.py\` with percentage bounds validation and unit tests in \`tests/test_billing.py\`.

## Log
2026-11-26T08:00Z started w1 on lane/billing (agent worker-1) | branch lane/billing | wind-down 2026-11-26T08:50Z | ends 2026-11-26T09:00Z
2026-11-26T08:25Z note: step 1 committed on lane/billing (${STEP1_SHA:0:7}); step 2 pending
EOF
