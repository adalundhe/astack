#!/bin/bash
set -euo pipefail
mkdir -p program/astack_home/billing/lessons/tax-rounding \
         program/astack_home/billing/lessons/old-vat \
         program/astack_home/billing/architecture \
         program/astack_home/billing/docs/contracts \
         repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/billing.py <<'EOF'
"""Billing v2 invoice service (integer-cent line items)."""
from __future__ import annotations

from typing import Any


def handle_create_invoice(headers: dict[str, str], payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Create a v2 invoice payload (tax calculation hook pending implementation)."""
    if not headers.get("Idempotency-Key"):
        return 400, {"error": "Idempotency-Key header is required"}
    line_items = payload.get("line_items", [])
    currency = str(payload.get("currency") or "USD").upper()
    subtotal_cents = sum(int(item["qty"]) * int(item["unit_price_cents"]) for item in line_items)
    return 201, {
        "currency": currency,
        "subtotal_cents": subtotal_cents,
        "tax_cents": 0,
        "total_cents": subtotal_cents,
    }
EOF

cat > repo/tests/test_billing.py <<'EOF'
import unittest
from src.billing import handle_create_invoice


class BillingTest(unittest.TestCase):
    def test_requires_idempotency_key(self):
        status, _ = handle_create_invoice({}, {"line_items": []})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial billing v2 invoice handler"

cat > program/astack_home/billing/lessons/tax-rounding/LESSON.md <<'EOF'
---
lesson: tax-rounding
project: billing
related_projects: [ledger-sync]
keywords: [tax, rounding, cents, basis-points, reconciliation]
status: active
created: 2026-06-14T15:00Z
updated: 2026-10-20T09:30Z
---

# Per-line half-up integer tax rounding

## Overview
Compute tax per line item in integer basis points using half-up rounding `(line_subtotal_cents * tax_rate_bps + 5000) // 10000`, then sum line taxes.
- **Applies when:** Computing `tax_cents` for single- or multi-line invoices in `billing` and `ledger-sync`.
- **Does not apply when:** Jurisdiction explicitly mandates invoice-level VAT aggregation outside US/EU standard rules.

## Skills and tools used
- **Skills:** `find-it`, `fix-it`
- **Tools / environments:** Python unittest, `ledger-sync` reconciliation harness

## Details
Rounding tax once at the invoice subtotal instead of per line caused 1-cent reconciliation drift against `ledger-sync` on multi-line invoices with odd cent amounts (e.g., 3 lines of 333 cents at 825 bps).

## Successes
- Switching to per-line `(line_subtotal_cents * tax_rate_bps + 5000) // 10000` eliminated all drift across 50,000 backfilled invoices.

## Issues
- Invoice-level total rounding fails `ledger-sync` penny parity checks.
- Python's built-in `round()` uses banker's half-to-even rounding and diverges on `.5` cent ties.

## Best path & guards
- **Next time:** Always round per line with integer half-up arithmetic and add a multi-line tie-case test (e.g., `unit_price_cents=100`, `tax_rate_bps=750`).
- **Structural guards:** Never import floats into `src/billing.py` tax paths.

## References
- `repo/src/billing.py`
- Related project: `ledger-sync`
EOF

cat > program/astack_home/billing/lessons/old-vat/LESSON.md <<'EOF'
---
lesson: old-vat
project: billing
related_projects: []
keywords: [vat, float, legacy, tax]
status: superseded
created: 2024-03-01T10:00Z
updated: 2026-02-12T11:00Z
---

# Legacy flat 15% float VAT helper (SUPERSEDED)

## Overview
SUPERSEDED by `tax-rounding` and `AD_1`. Previously recommended calling `legacy_vat_float(dollars) * 0.15` for all EU invoices.
- **Applies when:** Retired v1 billing pipeline (deleted in 2025).
- **Does not apply when:** Current `billing` v2 integer-cent codebase.

## Skills and tools used
- **Skills:** `find-it`
- **Tools / environments:** Legacy Python v1

## Details
Float arithmetic introduced rounding drift and `legacy_vat_float` was removed from `repo/src/billing.py`.

## Successes
- Historical reference only.

## Issues
- Floating-point drift violates `AD_1`.

## Best path & guards
- **Next time:** Do NOT use `legacy_vat_float` or flat 15% float VAT; follow `tax-rounding` and `AD_1`.
- **Structural guards:** None.

## References
- Superseded by `lessons/tax-rounding/LESSON.md` and `architecture/AD_1.md`.
EOF

cat > program/astack_home/billing/architecture/AD_1.md <<'EOF'
---
ad_number: 1
name: Integer minor-unit storage
description: Represent and compute all invoice prices, taxes, and totals as integer minor-unit *_cents fields with zero floating-point arithmetic.
---

# AD-1: Integer minor-unit storage

## Status

Accepted (2026-02-10). Built (2026-02-14).

## Context

Floating-point dollar math caused penny drift across multi-line invoice totals and settlement ledgers.

## Decision

All internal APIs, storage schemas, and calculators in `billing` MUST use integer minor units (`unit_price_cents`, `subtotal_cents`, `tax_cents`, `total_cents`) and integer basis points (`tax_rate_bps`). Floating-point types are prohibited in money calculations.

## Non-goals

Display string formatting at UI presentation boundaries.

## Costs accepted

Callers must supply `unit_price_cents` and `tax_rate_bps` as integers.

## Alternatives considered

`Decimal` everywhere was rejected due to JSON wire serialization ambiguity with downstream consumers.

## Acceptance criteria

All invoice arithmetic in `repo/src/billing.py` uses exact integer math.

## Tests

Unit tests assert integer output types (`isinstance(..., int)` and not `float`).

## Evidence

Verified against `repo/src/billing.py` and `ledger-sync` settlement reports.
EOF

cat > program/astack_home/billing/docs/contracts/api.md <<'EOF'
# Billing Public HTTP Contract (`POST /v2/invoices`)

## Request
- **Required header:** `Idempotency-Key` (HTTP 400 if omitted).
- **Body fields:**
  - `line_items`: list of `{qty: int, unit_price_cents: int, tax_rate_bps: int}`.
  - `currency`: optional ISO-4217 code, defaults to `"USD"` for backwards compatibility.

## Response (`201 Created`)
- JSON object with exact integer minor-unit fields:
  - `currency: str`
  - `subtotal_cents: int`
  - `tax_cents: int`
  - `total_cents: int` (`subtotal_cents + tax_cents`)

## Compatibility Rules
- Never return floating-point dollar fields or drop the default `currency="USD"` fallback.
EOF
