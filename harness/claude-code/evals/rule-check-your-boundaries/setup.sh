#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Webhook Invoice Processor

Processes incoming HTTP/JSON billing webhook payloads in `src/webhooks.py`.

## Public Contract

### `parse_webhook_payload(raw_payload: str | bytes | dict)`
Parses and validates an untrusted webhook payload once at the boundary into a typed domain object (dataclass, not a raw `dict`). Raises `ValueError` on any invalid or malformed input.

Expected JSON object fields:
- `event_id`: non-empty `str` (trimmed).
- `customer_id`: non-empty `str` (trimmed).
- `currency`: 3-letter uppercase ASCII currency code (for example `"USD"`, `"EUR"`).
- `items`: non-empty `list` of item objects, each with:
  - `sku`: non-empty `str` (trimmed)
  - `unit_price_cents`: `int` strictly greater than `0` (booleans must be rejected)
  - `quantity`: `int` strictly greater than `0` (booleans must be rejected)
- `discount_code` (optional): `None` / omitted, `"SAVE10"` (10% off via `subtotal * 90 // 100`), or `"SAVE20"` (20% off via `subtotal * 80 // 100`). Any other value is invalid.

### Core helpers
- `calculate_subtotal(invoice) -> int`: takes the parsed domain object (not a raw `dict`) and returns the integer subtotal in cents without redundant dict validation.
- `apply_discount(invoice, subtotal_cents: int) -> int`: takes the parsed domain object (not a raw `dict`) and returns the final integer total in cents without redundant dict validation.

### `handle_webhook(raw_payload: str | bytes | dict) -> dict`
Entry point for incoming webhook deliveries:
- On valid payload, returns:
  `{"status": 200, "event_id": ..., "customer_id": ..., "currency": ..., "subtotal_cents": int, "total_cents": int}`
- On malformed or invalid payload, returns:
  `{"status": 400, "error": "<non-empty reason>"}`
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/webhooks.py <<'EOF'
from __future__ import annotations

import json
from typing import Any


def calculate_subtotal(payload: dict[str, Any]) -> int:
    if not payload or not isinstance(payload, dict) or "items" not in payload or payload["items"] is None:
        raise ValueError("missing items")
    total = 0
    for item in payload["items"]:
        if not isinstance(item, dict):
            raise ValueError("invalid item")
        total += int(item["unit_price_cents"]) * int(item["quantity"])
    return total


def apply_discount(payload: dict[str, Any], subtotal_cents: int) -> int:
    code = payload.get("discount_code") if isinstance(payload, dict) else None
    if code == "SAVE10":
        return subtotal_cents * 90 // 100
    if code == "SAVE20":
        return subtotal_cents * 80 // 100
    return subtotal_cents


def handle_webhook(raw_payload: str | bytes | dict[str, Any]) -> dict[str, Any]:
    body = json.loads(raw_payload) if isinstance(raw_payload, (str, bytes)) else raw_payload
    subtotal = calculate_subtotal(body)
    final = apply_discount(body, subtotal)
    return {
        "status": 200,
        "event_id": body.get("event_id") if isinstance(body, dict) else None,
        "customer_id": body.get("customer_id") if isinstance(body, dict) else None,
        "currency": body.get("currency") if isinstance(body, dict) else None,
        "subtotal_cents": subtotal,
        "total_cents": final,
    }
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_webhooks.py <<'EOF'
import json
import unittest

from src.webhooks import handle_webhook


class WebhookProcessorTest(unittest.TestCase):
    def test_valid_webhook_without_discount(self):
        payload = json.dumps({
            "event_id": "evt-001",
            "customer_id": "cust-42",
            "currency": "USD",
            "items": [
                {"sku": "plan-pro", "unit_price_cents": 2500, "quantity": 2},
                {"sku": "addon-sso", "unit_price_cents": 1000, "quantity": 1},
            ],
        })
        resp = handle_webhook(payload)
        self.assertEqual(resp["status"], 200)
        self.assertEqual(resp["event_id"], "evt-001")
        self.assertEqual(resp["customer_id"], "cust-42")
        self.assertEqual(resp["currency"], "USD")
        self.assertEqual(resp["subtotal_cents"], 6000)
        self.assertEqual(resp["total_cents"], 6000)

    def test_valid_webhook_with_discount(self):
        resp = handle_webhook({
            "event_id": "evt-002",
            "customer_id": "cust-99",
            "currency": "EUR",
            "items": [{"sku": "seat", "unit_price_cents": 1000, "quantity": 3}],
            "discount_code": "SAVE10",
        })
        self.assertEqual(resp["status"], 200)
        self.assertEqual(resp["subtotal_cents"], 3000)
        self.assertEqual(resp["total_cents"], 2700)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
