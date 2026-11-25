#!/usr/bin/env python3
"""Objective post-run verifier for vectored-review-planted-bugs.

Checks that `repo/` was untouched AND executes saved reproduction scripts against:
  - the buggy branch under review (must fail),
  - a cleanly fixed copy of all 5 planted bugs (must pass, rejecting decoy attacks & broken scripts), and
  - 5 leave-one-bug-in copies (proving which specific planted bugs were reproduced).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _repro_verify import PlantedBug, verify_reproductions  # noqa: E402


def fix_bug1_coupon_gt_100(repo: Path) -> None:
    p = repo / "src" / "pricing.py"
    text = p.read_text(encoding="utf-8")
    old = '    if coupon_pct < 0:\n        raise ValueError("coupon percentage cannot be negative")'
    new = '    if coupon_pct < 0 or coupon_pct > 100:\n        raise ValueError("coupon percentage must be between 0 and 100")'
    assert old in text, "bug1 anchor missing in pricing.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def fix_bug2_duplicate_sku_batch(repo: Path) -> None:
    """Fix single-threaded duplicate-SKU oversell without removing the split-lock race if still present."""
    p = repo / "src" / "inventory.py"
    text = p.read_text(encoding="utf-8")
    old = (
        "        with self._lock:\n"
        "            for sku, qty in items:\n"
        "                if self._stock.get(sku, 0) < qty:\n"
        '                    raise ValueError(f"insufficient stock for {sku}")'
    )
    new = (
        "        totals: dict[str, int] = {}\n"
        "        for sku, qty in items:\n"
        "            totals[sku] = totals.get(sku, 0) + qty\n"
        "        with self._lock:\n"
        "            for sku, qty in totals.items():\n"
        "                if self._stock.get(sku, 0) < qty:\n"
        '                    raise ValueError(f"insufficient stock for {sku}")'
    )
    assert old in text, "bug2 anchor missing in inventory.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def fix_bug3_split_lock_race(repo: Path) -> None:
    """Combine validation and commit under a single lock acquisition (orthogonal to bug2)."""
    p = repo / "src" / "inventory.py"
    text = p.read_text(encoding="utf-8")
    old = (
        "        # Release between validation and commit so callers don't block readers during check\n"
        "        with self._lock:\n"
        "            for sku, qty in items:\n"
        "                self._stock[sku] = self._stock.get(sku, 0) - qty"
    )
    new = (
        "            for sku, qty in items:\n"
        "                self._stock[sku] = self._stock.get(sku, 0) - qty"
    )
    assert old in text, "bug3 anchor missing in inventory.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def fix_bug4_wal_pipe_delimiter_seam(repo: Path) -> None:
    """Replace fragile pipe-delimited WAL encoding with JSON lines so `|` in idem_key never corrupts replay."""
    p = repo / "src" / "journal.py"
    p.write_text(
        '''from __future__ import annotations

import json
import os
from pathlib import Path
from src.models import Order


class OrderJournal:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    @staticmethod
    def _encode(order_id: str, idem_key: str, total_cents: int, status: str) -> str:
        return json.dumps(
            {
                "order_id": order_id,
                "idem_key": idem_key,
                "total_cents": total_cents,
                "status": status,
            }
        ) + "\\n"

    def append_order(self, order: Order) -> None:
        line = self._encode(order.order_id, order.idem_key, order.total_cents, order.status)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def append_refund(self, order_id: str, amount_cents: int, known_orders: dict[str, Order]) -> None:
        existing = known_orders.get(order_id)
        if existing is None or existing.status != "paid":
            raise ValueError(f"cannot refund order {order_id}")
        line = self._encode(order_id, existing.idem_key, -amount_cents, "refunded")
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def replay(self) -> dict[str, Order]:
        orders: dict[str, Order] = {}
        raw = self.path.read_text(encoding="utf-8")
        for line in raw.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            orders[row["order_id"]] = Order(
                order_id=row["order_id"],
                idem_key=row["idem_key"],
                total_cents=int(row["total_cents"]),
                status=row["status"],
            )
        return orders

    def rotate_snapshot(self, orders: dict[str, Order]) -> None:
        """Rewrite journal compactly via atomic write-then-replace (safe under caller lock)."""
        tmp = self.path.with_name(f".{self.path.name}.tmp")
        rows = [
            self._encode(o.order_id, o.idem_key, o.total_cents, o.status)
            for _, o in sorted(orders.items())
        ]
        tmp.write_text("".join(rows), encoding="utf-8")
        os.replace(tmp, self.path)
''',
        encoding="utf-8",
    )


def fix_bug5_refund_cache_poisoning(repo: Path) -> None:
    """Persist refund in journal BEFORE mutating in-memory caches so failed refunds never poison state."""
    p = repo / "src" / "service.py"
    text = p.read_text(encoding="utf-8")
    old = (
        "            # Update cached revenue & status first, then record refund in journal\n"
        '            self._status_cache[order_id] = "refunded"\n'
        "            self._revenue_cache -= amount\n"
        "            self._journal.append_refund(order_id, amount, self._orders)\n"
        "            self._orders[order_id] = Order(\n"
        "                order_id=order.order_id,\n"
        "                idem_key=order.idem_key,\n"
        "                total_cents=0,\n"
        '                status="refunded",\n'
        "            )\n"
        "            self._journal.rotate_snapshot(self._orders)"
    )
    new = (
        "            self._journal.append_refund(order_id, amount, self._orders)\n"
        "            assert order is not None\n"
        "            updated = dict(self._orders)\n"
        "            updated[order_id] = Order(\n"
        "                order_id=order.order_id,\n"
        "                idem_key=order.idem_key,\n"
        "                total_cents=0,\n"
        '                status="refunded",\n'
        "            )\n"
        "            self._journal.rotate_snapshot(updated)\n"
        "            self._orders = updated\n"
        '            self._status_cache[order_id] = "refunded"\n'
        "            self._revenue_cache -= amount"
    )
    assert old in text, "bug5 anchor missing in service.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


PLANTED_BUGS = [
    PlantedBug("bug1_coupon_gt_100", "apply_coupon allows coupon_pct > 100", fix_bug1_coupon_gt_100, attempts=1),
    PlantedBug("bug2_duplicate_sku_batch", "reserve_batch oversells repeated SKUs in one batch", fix_bug2_duplicate_sku_batch, attempts=1),
    PlantedBug("bug3_split_lock_race", "reserve_batch split lock causes concurrent oversell", fix_bug3_split_lock_race, attempts=3),
    PlantedBug("bug4_wal_pipe_delimiter_seam", "idem_key pipe delimiter corrupts WAL replay", fix_bug4_wal_pipe_delimiter_seam, attempts=1),
    PlantedBug("bug5_refund_cache_poisoning", "refund_order poisons caches before journal validation", fix_bug5_refund_cache_poisoning, attempts=1),
]


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    code, _ = verify_reproductions(
        ws,
        PLANTED_BUGS,
        min_proven=4,
        require_any=("bug4_wal_pipe_delimiter_seam", "bug5_refund_cache_poisoning"),
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
