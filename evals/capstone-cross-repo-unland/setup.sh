#!/usr/bin/env bash
set -euo pipefail

mkdir -p program repo-core/src repo-core/tests repo-core/docs repo-service/src repo-service/tests

cat > program/brief.md <<'EOF'
# Cross-Repo Release Recovery Brief

## Situation

- `./repo-core` provides pricing calculation logic (`src/pricing.py:calculate_total`).
- `./repo-service` imports `calculate_total` from `../repo-core/src` across billing, invoices, and webhook dispatch.
- A recent change in `./repo-core` altered `calculate_total` from returning an `int` to returning a `dict`, followed by an unrelated documentation commit (`docs/CHANGELOG.md` and `README.md`) landed on top of it.
- `./repo-service`'s test suite is now failing, and `program/release-plan.json` currently uses floating `"main"` references and deploys `repo-service` before `repo-core`.

## Deliverables

1. Write `program/BLAST_RADIUS.md` identifying every breaking caller in `./repo-service` (`billing.py:<line>`, `invoices.py:<line>`, `webhooks.py:<line>`), how each reaches `calculate_total`, and the concrete failure mode.
2. Safely revert **only** the breaking return-shape commit in `./repo-core` without rewriting history or dropping the subsequent documentation commit.
3. Update `program/release-plan.json` so:
   - zero floating refs (`main`, `master`, `HEAD`, `latest`) remain;
   - exact 40-character post-revert `HEAD` SHAs of `repo-core` and `repo-service` are pinned;
   - `repo-core` precedes `repo-service` with explicit `depends_on`.
4. Leave both `./repo-core` and `./repo-service` clean with both unit test suites passing.
EOF

# --- repo-core Commit A (good int return) ---
cat > repo-core/src/__init__.py <<'EOF'
"""Core pricing library."""
EOF

cat > repo-core/src/pricing.py <<'EOF'
"""Core pricing calculator."""
from __future__ import annotations


def calculate_total(items: list[dict[str, int]]) -> int:
    """Return total amount in integer cents across line items."""
    total = 0
    for item in items:
        qty = int(item.get("qty", 1))
        unit_cents = int(item["unit_cents"])
        if qty < 0 or unit_cents < 0:
            raise ValueError("qty and unit_cents must be non-negative")
        total += qty * unit_cents
    return total
EOF

cat > repo-core/tests/test_pricing.py <<'EOF'
"""Unit tests for repo-core pricing."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pricing import calculate_total


class PricingTests(unittest.TestCase):
    def test_calculate_total_returns_integer_cents(self) -> None:
        total = calculate_total([{"qty": 2, "unit_cents": 450}, {"qty": 1, "unit_cents": 100}])
        self.assertEqual(total, 1000)
        self.assertIsInstance(total, int)

    def test_rejects_negative_values(self) -> None:
        with self.assertRaises(ValueError):
            calculate_total([{"qty": -1, "unit_cents": 100}])


if __name__ == "__main__":
    unittest.main()
EOF

cat > repo-core/README.md <<'EOF'
# repo-core

Shared pricing calculations.
EOF

git -C repo-core init -q -b main
git -C repo-core config user.name "Eval Fixture"
git -C repo-core config user.email "eval@example.invalid"
git -C repo-core add .
git -C repo-core commit -q -m "feat: initial integer-cents pricing calculator"
git -C repo-core rev-parse HEAD > program/commit_a.txt

# --- repo-core Commit B (breaking return-shape change to dict) ---
cat > repo-core/src/pricing.py <<'EOF'
"""Core pricing calculator."""
from __future__ import annotations


def calculate_total(items: list[dict[str, int]]) -> dict[str, object]:
    """BREAKING: returns dict envelope instead of integer cents."""
    total = 0
    for item in items:
        qty = int(item.get("qty", 1))
        unit_cents = int(item["unit_cents"])
        if qty < 0 or unit_cents < 0:
            raise ValueError("qty and unit_cents must be non-negative")
        total += qty * unit_cents
    return {"total_cents": total, "currency": "USD"}
EOF

cat > repo-core/tests/test_pricing.py <<'EOF'
"""Unit tests for repo-core pricing."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pricing import calculate_total


class PricingTests(unittest.TestCase):
    def test_calculate_total_returns_dict_envelope(self) -> None:
        result = calculate_total([{"qty": 2, "unit_cents": 450}, {"qty": 1, "unit_cents": 100}])
        self.assertEqual(result, {"total_cents": 1000, "currency": "USD"})

    def test_rejects_negative_values(self) -> None:
        with self.assertRaises(ValueError):
            calculate_total([{"qty": -1, "unit_cents": 100}])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo-core add src/pricing.py tests/test_pricing.py
git -C repo-core commit -q -m "feat!: return currency dict from calculate_total"
git -C repo-core rev-parse HEAD > program/commit_b.txt

# --- repo-core Commit C (good unrelated docs commit on top of B) ---
cat > repo-core/docs/CHANGELOG.md <<'EOF'
# Changelog

## 1.4.0
- Documented pricing rounding conventions and audit trail fields.
EOF

cat > repo-core/README.md <<'EOF'
# repo-core

Shared pricing calculations. See `docs/CHANGELOG.md` for release notes.
EOF

git -C repo-core add docs/CHANGELOG.md README.md
git -C repo-core commit -q -m "docs: add changelog and release notes link"
git -C repo-core rev-parse HEAD > program/commit_c.txt

# --- repo-service (imports repo-core across 3 callers) ---
cat > repo-service/src/__init__.py <<'EOF'
"""Downstream billing service depending on repo-core."""
EOF

cat > repo-service/src/billing.py <<'EOF'
"""Direct billing caller of repo-core pricing."""
from __future__ import annotations

import sys
from pathlib import Path

_CORE_SRC = Path(__file__).resolve().parents[2] / "repo-core" / "src"
if str(_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_CORE_SRC))

from pricing import calculate_total


def build_charge(items: list[dict[str, int]]) -> dict[str, int]:
    subtotal = calculate_total(items)
    platform_fee = subtotal // 10
    return {
        "subtotal_cents": subtotal,
        "fee_cents": platform_fee,
        "grand_total_cents": subtotal + platform_fee,
    }
EOF

cat > repo-service/src/invoices.py <<'EOF'
"""Invoice formatter using aliased calculate_total import."""
from __future__ import annotations

import sys
from pathlib import Path

_CORE_SRC = Path(__file__).resolve().parents[2] / "repo-core" / "src"
if str(_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(_CORE_SRC))

from pricing import calculate_total as compute_cents


def format_invoice_amount(items: list[dict[str, int]]) -> str:
    cents = compute_cents(items)
    return f"${cents / 100:.2f}"
EOF

cat > repo-service/src/webhooks.py <<'EOF'
"""Outbound webhook payload builder (two-hop caller via billing.build_charge)."""
from __future__ import annotations

from billing import build_charge


def build_payment_event(order_id: str, items: list[dict[str, int]]) -> dict[str, object]:
    charge = build_charge(items)
    amount_cents = charge["grand_total_cents"]
    if not isinstance(amount_cents, int) or amount_cents < 0:
        raise TypeError(f"expected non-negative int amount_cents, got {type(amount_cents).__name__}")
    return {
        "event": "payment.created",
        "order_id": order_id,
        "amount_cents": amount_cents,
    }
EOF

cat > repo-service/tests/test_service.py <<'EOF'
"""Downstream integration tests against repo-core."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from billing import build_charge
from invoices import format_invoice_amount
from webhooks import build_payment_event


class ServiceIntegrationTests(unittest.TestCase):
    def test_billing_charge_math(self) -> None:
        charge = build_charge([{"qty": 2, "unit_cents": 500}])
        self.assertEqual(charge, {"subtotal_cents": 1000, "fee_cents": 100, "grand_total_cents": 1100})

    def test_invoice_formatting(self) -> None:
        self.assertEqual(format_invoice_amount([{"qty": 3, "unit_cents": 250}]), "$7.50")

    def test_webhook_payload(self) -> None:
        ev = build_payment_event("ord-7", [{"qty": 1, "unit_cents": 1000}])
        self.assertEqual(ev, {"event": "payment.created", "order_id": "ord-7", "amount_cents": 1100})


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo-service init -q -b main
git -C repo-service config user.name "Eval Fixture"
git -C repo-service config user.email "eval@example.invalid"
git -C repo-service add .
git -C repo-service commit -q -m "feat: initial billing, invoices, and webhook callers"
git -C repo-service rev-parse HEAD > program/service_base_sha.txt

# --- Broken release-plan.json (floating refs + wrong order) ---
cat > program/release-plan.json <<'EOF'
{
  "release_id": "rel-2026-11-26",
  "steps": [
    {
      "id": "deploy-service",
      "repo": "repo-service",
      "ref": "main",
      "depends_on": []
    },
    {
      "id": "deploy-core",
      "repo": "repo-core",
      "ref": "main",
      "depends_on": ["deploy-service"]
    }
  ]
}
EOF
