"""Separated offline oracle for `rule-check-your-boundaries`."""
from __future__ import annotations

from pathlib import Path

FIXED_SRC = '''from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

_DISCOUNT_RATES: dict[str, int] = {
    "SAVE10": 90,
    "SAVE20": 80,
}


@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price_cents: int
    quantity: int


@dataclass(frozen=True)
class WebhookInvoice:
    event_id: str
    customer_id: str
    currency: str
    items: tuple[LineItem, ...]
    discount_code: str | None = None


def _require_non_empty_str(mapping: dict[str, Any], field: str) -> str:
    raw = mapping.get(field)
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return raw.strip()


def _require_positive_int(mapping: dict[str, Any], field: str) -> int:
    raw = mapping.get(field)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return raw


def parse_webhook_payload(raw_payload: str | bytes | dict[str, Any]) -> WebhookInvoice:
    if isinstance(raw_payload, (str, bytes)):
        try:
            decoded = json.loads(raw_payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"malformed JSON payload: {exc}") from exc
    elif isinstance(raw_payload, dict):
        decoded = raw_payload
    else:
        raise ValueError("payload must be a JSON string, bytes, or dict")

    if not isinstance(decoded, dict):
        raise ValueError("payload root must be a JSON object")

    event_id = _require_non_empty_str(decoded, "event_id")
    customer_id = _require_non_empty_str(decoded, "customer_id")

    raw_currency = decoded.get("currency")
    if not isinstance(raw_currency, str) or len(raw_currency) != 3 or not raw_currency.isascii() or not raw_currency.isupper() or not raw_currency.isalpha():
        raise ValueError("currency must be a 3-letter uppercase ASCII code")

    raw_items = decoded.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("items must be a non-empty list")

    items: list[LineItem] = []
    for idx, entry in enumerate(raw_items):
        if not isinstance(entry, dict):
            raise ValueError(f"items[{idx}] must be an object")
        sku = _require_non_empty_str(entry, "sku")
        unit_price_cents = _require_positive_int(entry, "unit_price_cents")
        quantity = _require_positive_int(entry, "quantity")
        items.append(LineItem(sku=sku, unit_price_cents=unit_price_cents, quantity=quantity))

    discount_code = decoded.get("discount_code")
    if discount_code is not None:
        if not isinstance(discount_code, str) or discount_code not in _DISCOUNT_RATES:
            raise ValueError(f"unsupported discount_code: {discount_code!r}")

    return WebhookInvoice(
        event_id=event_id,
        customer_id=customer_id,
        currency=raw_currency,
        items=tuple(items),
        discount_code=discount_code,
    )


def calculate_subtotal(invoice: WebhookInvoice) -> int:
    return sum(item.unit_price_cents * item.quantity for item in invoice.items)


def apply_discount(invoice: WebhookInvoice, subtotal_cents: int) -> int:
    if invoice.discount_code is None:
        return subtotal_cents
    return subtotal_cents * _DISCOUNT_RATES[invoice.discount_code] // 100


def handle_webhook(raw_payload: str | bytes | dict[str, Any]) -> dict[str, Any]:
    try:
        invoice = parse_webhook_payload(raw_payload)
    except ValueError as exc:
        return {"status": 400, "error": str(exc)}

    subtotal = calculate_subtotal(invoice)
    final = apply_discount(invoice, subtotal)
    return {
        "status": 200,
        "event_id": invoice.event_id,
        "customer_id": invoice.customer_id,
        "currency": invoice.currency,
        "subtotal_cents": subtotal,
        "total_cents": final,
    }
'''

FIXED_TESTS = '''import json
import unittest

from src.webhooks import (
    WebhookInvoice,
    apply_discount,
    calculate_subtotal,
    handle_webhook,
    parse_webhook_payload,
)


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

    def test_parse_produces_typed_domain_object_for_core_helpers(self):
        invoice = parse_webhook_payload({
            "event_id": " evt-3 ",
            "customer_id": " cust-3 ",
            "currency": "GBP",
            "items": [{"sku": " tier-1 ", "unit_price_cents": 500, "quantity": 4}],
            "discount_code": "SAVE20",
        })
        self.assertIsInstance(invoice, WebhookInvoice)
        self.assertEqual(invoice.event_id, "evt-3")
        self.assertEqual(calculate_subtotal(invoice), 2000)
        self.assertEqual(apply_discount(invoice, 2000), 1600)

    def test_malformed_json_and_non_object_return_400(self):
        for raw in ("{bad json", "[1, 2, 3]", b"not-json"):
            with self.assertRaises(ValueError):
                parse_webhook_payload(raw)
            resp = handle_webhook(raw)
            self.assertEqual(resp["status"], 400)
            self.assertTrue(resp["error"])

    def test_invalid_boundary_fields_are_rejected(self):
        base = {
            "event_id": "evt-9",
            "customer_id": "cust-9",
            "currency": "USD",
            "items": [{"sku": "item-1", "unit_price_cents": 100, "quantity": 1}],
        }
        invalid_payloads = [
            {**base, "event_id": "   "},
            {**base, "customer_id": ""},
            {**base, "currency": "usd"},
            {**base, "items": []},
            {**base, "items": ["not-an-object"]},
            {**base, "items": [{"sku": "a", "unit_price_cents": -5, "quantity": 1}]},
            {**base, "items": [{"sku": "a", "unit_price_cents": 100, "quantity": 0}]},
            {**base, "items": [{"sku": "a", "unit_price_cents": True, "quantity": 1}]},
            {**base, "items": [{"sku": "a", "unit_price_cents": 100, "quantity": True}]},
            {**base, "discount_code": "FREE100"},
        ]
        for bad in invalid_payloads:
            with self.assertRaises(ValueError):
                parse_webhook_payload(bad)
            resp = handle_webhook(bad)
            self.assertEqual(resp["status"], 400)
            self.assertTrue(resp["error"])


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "webhooks.py").write_text(FIXED_SRC, encoding="utf-8")
    (repo / "tests" / "test_webhooks.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Refactored src/webhooks.py to parse and validate incoming webhook payloads once "
            "at the boundary into frozen LineItem and WebhookInvoice dataclasses, stripped raw-dict "
            "re-checks from calculate_subtotal and apply_discount, returned HTTP 400 error payloads "
            "for invalid inputs, and added unit tests covering valid and malformed payloads."
        ),
    }
