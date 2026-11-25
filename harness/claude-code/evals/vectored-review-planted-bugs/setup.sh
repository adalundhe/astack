#!/bin/bash
set -euo pipefail
mkdir -p program/repros repo/src repo/tests
if [ -n "${ASTACK_EVAL_SETTINGS_JSON:-}" ]; then
  printf '%s\n' "$ASTACK_EVAL_SETTINGS_JSON" > program/settings.json
else
cat > program/settings.json <<'EOF'
{
  "roles": {
    "worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  },
  "reviewer_pool": [
    {"provider": "anthropic", "model": "opus", "effort": "medium"},
    {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
    {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  ]
}
EOF
fi

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF
cat > repo/src/models.py <<'EOF'
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LineItem:
    sku: str
    qty: int
    unit_price_cents: int


@dataclass(frozen=True)
class Order:
    order_id: str
    idem_key: str
    total_cents: int
    status: str
EOF
cat > repo/src/inventory.py <<'EOF'
from __future__ import annotations

import threading


class Inventory:
    def __init__(self, initial: dict[str, int]):
        self._lock = threading.Lock()
        self._stock: dict[str, int] = dict(initial)

    def available(self, sku: str) -> int:
        with self._lock:
            return self._stock.get(sku, 0)

    def reserve_one(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        with self._lock:
            if self._stock.get(sku, 0) < qty:
                raise ValueError(f"insufficient stock for {sku}")
            self._stock[sku] = self._stock[sku] - qty
EOF
cat > repo/tests/test_orders.py <<'EOF'
import unittest
from src.inventory import Inventory


class BaseInventoryTest(unittest.TestCase):
    def test_reserve_one(self):
        inv = Inventory({"sku-a": 5})
        inv.reserve_one("sku-a", 3)
        self.assertEqual(inv.available("sku-a"), 2)
        with self.assertRaises(ValueError):
            inv.reserve_one("sku-a", 3)


if __name__ == "__main__":
    unittest.main()
EOF
git -C repo add .
git -C repo commit -q -m "initial models and single-SKU inventory"
git -C repo rev-parse HEAD > program/base_sha.txt

# Branch `lane/order-checkout` adds multi-file order checkout, coupons, batch inventory,
# WAL journal persistence, and refunds with 5 planted blocking bugs of varying difficulty
# + 1 false-positive decoy + 1 minor nit — while ALL shipped unit tests pass cleanly!
#   Bug 1 (Easy): pricing.apply_coupon allows coupon_pct > 100 -> negative order totals.
#   Bug 2 (Medium): inventory.reserve_batch validates each item against self._stock without
#                   accumulating repeated SKUs in the same batch -> single-threaded oversell.
#   Bug 3 (Medium-Hard): inventory.reserve_batch splits validation and mutation across two locks
#                        -> concurrent checkout oversell race.
#   Bug 4 (Hard SEAM): service.py constructs idem_key = f"{tenant}|{client_key}" containing `|`,
#                      while journal.py writes pipe-delimited WAL rows and replays via
#                      `line.split("|", 3)` -> breaks/corrupts every journal replay on restart.
#   Bug 5 (Hard state/cache): service.refund_order mutates _revenue_cache and _status_cache
#                             BEFORE journal.append_refund validates/persists -> poisoned cache
#                             on failed refund (e.g. unknown or already-refunded order or IO error).
#   Decoy (NOT a bug): journal.rotate_snapshot uses atomic tempfile + os.replace under caller lock.
#   Minor nit: redundant `# compute subtotal` narrating comment in pricing.py.
git -C repo checkout -q -b lane/order-checkout

cat > repo/src/pricing.py <<'EOF'
from __future__ import annotations

from src.models import LineItem


def calculate_subtotal(items: list[LineItem]) -> int:
    if not items:
        raise ValueError("order must have at least one item")
    # compute subtotal
    total = 0
    for item in items:
        if item.qty <= 0 or item.unit_price_cents < 0:
            raise ValueError("invalid line item")
        total += item.qty * item.unit_price_cents
    return total


def apply_coupon(subtotal_cents: int, coupon_pct: int) -> int:
    if coupon_pct < 0:
        raise ValueError("coupon percentage cannot be negative")
    discount = (subtotal_cents * coupon_pct) // 100
    return subtotal_cents - discount
EOF

cat > repo/src/inventory.py <<'EOF'
from __future__ import annotations

import threading


class Inventory:
    def __init__(self, initial: dict[str, int]):
        self._lock = threading.Lock()
        self._stock: dict[str, int] = dict(initial)

    def available(self, sku: str) -> int:
        with self._lock:
            return self._stock.get(sku, 0)

    def reserve_one(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        with self._lock:
            if self._stock.get(sku, 0) < qty:
                raise ValueError(f"insufficient stock for {sku}")
            self._stock[sku] = self._stock[sku] - qty

    def reserve_batch(self, items: list[tuple[str, int]]) -> None:
        if not items:
            raise ValueError("empty reservation batch")
        for sku, qty in items:
            if qty <= 0:
                raise ValueError("qty must be positive")
        with self._lock:
            for sku, qty in items:
                if self._stock.get(sku, 0) < qty:
                    raise ValueError(f"insufficient stock for {sku}")
        # Release between validation and commit so callers don't block readers during check
        with self._lock:
            for sku, qty in items:
                self._stock[sku] = self._stock.get(sku, 0) - qty
EOF

cat > repo/src/journal.py <<'EOF'
from __future__ import annotations

import os
from pathlib import Path
from src.models import Order


class OrderJournal:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def append_order(self, order: Order) -> None:
        line = f"{order.order_id}|{order.idem_key}|{order.total_cents}|{order.status}\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def append_refund(self, order_id: str, amount_cents: int, known_orders: dict[str, Order]) -> None:
        existing = known_orders.get(order_id)
        if existing is None or existing.status != "paid":
            raise ValueError(f"cannot refund order {order_id}")
        line = f"{order_id}|{existing.idem_key}|{-amount_cents}|refunded\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def replay(self) -> dict[str, Order]:
        orders: dict[str, Order] = {}
        raw = self.path.read_text(encoding="utf-8")
        for line in raw.splitlines():
            if not line.strip():
                continue
            order_id, idem_key, total_raw, status = line.split("|", 3)
            orders[order_id] = Order(
                order_id=order_id,
                idem_key=idem_key,
                total_cents=int(total_raw),
                status=status,
            )
        return orders

    def rotate_snapshot(self, orders: dict[str, Order]) -> None:
        """Rewrite journal compactly via atomic write-then-replace (safe under caller lock)."""
        tmp = self.path.with_name(f".{self.path.name}.tmp")
        rows = [
            f"{o.order_id}|{o.idem_key}|{o.total_cents}|{o.status}\n"
            for _, o in sorted(orders.items())
        ]
        tmp.write_text("".join(rows), encoding="utf-8")
        os.replace(tmp, self.path)
EOF

cat > repo/src/service.py <<'EOF'
from __future__ import annotations

import threading
from pathlib import Path
from src.inventory import Inventory
from src.journal import OrderJournal
from src.models import LineItem, Order
from src.pricing import apply_coupon, calculate_subtotal


class OrderService:
    def __init__(self, inventory: Inventory, journal_path: Path):
        self._lock = threading.Lock()
        self._inventory = inventory
        self._journal = OrderJournal(journal_path)
        self._orders: dict[str, Order] = self._journal.replay()
        self._by_idem: dict[str, Order] = {o.idem_key: o for o in self._orders.values()}
        self._status_cache: dict[str, str] = {oid: o.status for oid, o in self._orders.items()}
        self._revenue_cache: int = sum(o.total_cents for o in self._orders.values() if o.status == "paid")

    def total_revenue(self) -> int:
        return self._revenue_cache

    def status_of(self, order_id: str) -> str | None:
        return self._status_cache.get(order_id)

    def checkout(
        self,
        tenant_id: str,
        client_key: str,
        items: list[LineItem],
        coupon_pct: int = 0,
    ) -> Order:
        idem_key = f"{tenant_id}|{client_key}"
        with self._lock:
            if idem_key in self._by_idem:
                return self._by_idem[idem_key]
        subtotal = calculate_subtotal(items)
        total = apply_coupon(subtotal, coupon_pct)
        self._inventory.reserve_batch([(i.sku, i.qty) for i in items])
        with self._lock:
            order_id = f"ord-{len(self._orders) + 1}"
            order = Order(order_id=order_id, idem_key=idem_key, total_cents=total, status="paid")
            self._journal.append_order(order)
            self._orders[order_id] = order
            self._by_idem[idem_key] = order
            self._status_cache[order_id] = "paid"
            self._revenue_cache += total
            return order

    def refund_order(self, order_id: str) -> None:
        with self._lock:
            order = self._orders.get(order_id)
            amount = order.total_cents if order is not None else 0
            # Update cached revenue & status first, then record refund in journal
            self._status_cache[order_id] = "refunded"
            self._revenue_cache -= amount
            self._journal.append_refund(order_id, amount, self._orders)
            self._orders[order_id] = Order(
                order_id=order.order_id,
                idem_key=order.idem_key,
                total_cents=0,
                status="refunded",
            )
            self._journal.rotate_snapshot(self._orders)
EOF

cat > repo/tests/test_orders.py <<'EOF'
import tempfile
import unittest
from pathlib import Path
from src.inventory import Inventory
from src.models import LineItem
from src.service import OrderService


class OrderServiceTest(unittest.TestCase):
    def test_checkout_and_coupon_happy_path(self):
        with tempfile.TemporaryDirectory() as td:
            inv = Inventory({"sku-a": 10, "sku-b": 5})
            svc = OrderService(inv, Path(td) / "orders.wal")
            order = svc.checkout(
                "acme",
                "req-1",
                [LineItem("sku-a", 2, 500), LineItem("sku-b", 1, 1000)],
                coupon_pct=10,
            )
            self.assertEqual(order.total_cents, 1800)
            self.assertEqual(inv.available("sku-a"), 8)
            self.assertEqual(inv.available("sku-b"), 4)
            self.assertEqual(svc.total_revenue(), 1800)

    def test_idempotent_checkout_returns_same_order(self):
        with tempfile.TemporaryDirectory() as td:
            inv = Inventory({"sku-a": 10})
            svc = OrderService(inv, Path(td) / "orders.wal")
            o1 = svc.checkout("acme", "req-42", [LineItem("sku-a", 3, 200)])
            o2 = svc.checkout("acme", "req-42", [LineItem("sku-a", 3, 200)])
            self.assertEqual(o1.order_id, o2.order_id)
            self.assertEqual(inv.available("sku-a"), 7)

    def test_refund_paid_order(self):
        with tempfile.TemporaryDirectory() as td:
            inv = Inventory({"sku-a": 10})
            svc = OrderService(inv, Path(td) / "orders.wal")
            o = svc.checkout("acme", "req-9", [LineItem("sku-a", 1, 1000)])
            svc.refund_order(o.order_id)
            self.assertEqual(svc.status_of(o.order_id), "refunded")
            self.assertEqual(svc.total_revenue(), 0)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "add multi-file order checkout, coupons, WAL journal, and refunds"
git -C repo rev-parse HEAD > program/head_sha.txt
git -C repo diff main..lane/order-checkout > program/change.diff
