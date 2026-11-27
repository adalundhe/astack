#!/bin/bash
set -euo pipefail
mkdir -p program/astack_home/billing repo/docs repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/docs/spec.md <<'EOF'
# Billing Retry Specification

## Retry policy
- Failed invoice charges are retried within a **72-hour** retry window (`MAX_RETRY_WINDOW_HOURS = 72`).
- Each retry is recorded as a `dunning_attempt` linked to the invoice ID.
- Retries run synchronously inside the checkout HTTP handler so callers receive an immediate final status without a background queue.
EOF

cat > repo/src/billing.py <<'EOF'
"""Core billing charge entrypoints."""
from __future__ import annotations

from dataclasses import dataclass

MAX_RETRY_WINDOW_HOURS = 24
RETRY_LIMIT = 3
GATEWAY_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class RetryCharge:
    invoice_id: str
    attempt: int
    amount_cents: int
    status: str


def charge_invoice(invoice_id: str, amount_cents: int, gateway) -> RetryCharge:
    """Attempt a single synchronous payment gateway charge."""
    ok = gateway.charge(invoice_id=invoice_id, amount_cents=amount_cents, timeout=GATEWAY_TIMEOUT_SECONDS)
    return RetryCharge(
        invoice_id=invoice_id,
        attempt=1,
        amount_cents=amount_cents,
        status="paid" if ok else "failed",
    )
EOF

cat > repo/tests/test_billing.py <<'EOF'
import unittest
from src.billing import MAX_RETRY_WINDOW_HOURS, charge_invoice


class _StubGateway:
    def charge(self, invoice_id: str, amount_cents: int, timeout: int) -> bool:
        return True


class BillingTest(unittest.TestCase):
    def test_retry_window_and_charge(self):
        self.assertEqual(MAX_RETRY_WINDOW_HOURS, 24)
        rec = charge_invoice("inv-1", 2500, _StubGateway())
        self.assertEqual(rec.status, "paid")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial billing module and spec"

cat > program/request.md <<'EOF'
# Feature Request: Automatic Invoice Retries (project: billing)

We want to add automatic retries for failed invoice payments:

1. Callers must receive a final HTTP 200 receipt in under 500 ms p99, AND the checkout handler must synchronously complete up to 3 gateway retry attempts before returning so we avoid adding any async queue.
2. Failed invoices should retry automatically with unlimited attempts until payment succeeds, while also enforcing a strict 24-hour refund-window cutoff and guaranteeing zero duplicate charges.
3. Keep the domain model aligned with the existing billing spec and code.
EOF
