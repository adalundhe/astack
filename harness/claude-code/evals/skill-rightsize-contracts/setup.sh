#!/bin/bash
set -euo pipefail
mkdir -p program/astack_home/payments-sdk repo/src repo/examples repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/sdk.py <<'EOF'
"""Payments SDK public charge API with accumulated surface bloat."""
from __future__ import annotations

import os
from typing import Any


def create_charge(
    amount_cents: int | None = None,
    amount: int | None = None,
    currency: str = "USD",
    currency_code: str | None = None,
    customer_id: str | None = None,
    cust_id: str | None = None,
    api_key: str | None = None,
    environment: str | None = None,
    base_url: str | None = None,
    timeout_ms: int = 5000,
    timeout_seconds: float | None = None,
    retry_enabled: bool = True,
    max_retries: int = 2,
    legacy_xml_envelope: bool = False,
) -> dict[str, Any]:
    """Create a payment charge using 14 overlapping parameters plus a hidden env toggle."""
    resolved_amount = amount_cents if amount_cents is not None else amount
    if resolved_amount is None or resolved_amount <= 0:
        raise ValueError("positive amount_cents is required")

    resolved_currency = (currency_code or currency).upper()
    resolved_customer = customer_id or cust_id
    if not resolved_customer:
        raise ValueError("customer_id is required")

    key = api_key or os.environ.get("PAYMENTS_API_KEY", "")
    if not key:
        raise ValueError("api_key is required")

    # Redundant parameter: environment is already derivable from api_key prefix
    resolved_env = environment or ("live" if key.startswith("live_") else "test")
    resolved_url = base_url or (
        "https://api.payments.example/v1"
        if resolved_env == "live"
        else "https://sandbox.payments.example/v1"
    )
    resolved_timeout_ms = int(timeout_seconds * 1000) if timeout_seconds is not None else timeout_ms
    effective_retries = max_retries if retry_enabled else 0

    # Undocumented hidden toggle altering execution semantics silently
    force_sync = os.environ.get("PAYMENTS_SDK_FORCE_SYNC_FALLBACK", "").lower() in ("1", "true")

    # Dead bolt-on parameter: legacy_xml_envelope is ignored by v1 JSON API
    _ = legacy_xml_envelope

    return {
        "amount_cents": resolved_amount,
        "currency": resolved_currency,
        "customer_id": resolved_customer,
        "environment": resolved_env,
        "endpoint": resolved_url,
        "timeout_ms": resolved_timeout_ms,
        "max_retries": effective_retries,
        "sync_fallback": force_sync,
    }
EOF

cat > repo/examples/quickstart.py <<'EOF'
"""Tier-0 quickstart: charge a customer with minimal arguments."""
from src.sdk import create_charge

receipt = create_charge(
    amount_cents=2500,
    customer_id="cus_123",
    api_key="test_key_demo",
)
print(receipt)
EOF

cat > repo/tests/test_sdk.py <<'EOF'
import unittest
from src.sdk import create_charge


class SdkContractTest(unittest.TestCase):
    def test_basic_charge_defaults(self):
        res = create_charge(amount_cents=1500, customer_id="cus_1", api_key="test_abc")
        self.assertEqual(res["currency"], "USD")
        self.assertEqual(res["environment"], "test")
        self.assertEqual(res["timeout_ms"], 5000)
        self.assertEqual(res["max_retries"], 2)

    def test_custom_timeout_and_retries(self):
        res = create_charge(
            amount_cents=4900,
            currency="EUR",
            customer_id="cus_2",
            api_key="live_xyz",
            timeout_ms=12000,
            max_retries=0,
        )
        self.assertEqual(res["environment"], "live")
        self.assertEqual(res["timeout_ms"], 12000)
        self.assertEqual(res["max_retries"], 0)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial payments-sdk bloated public contract"
