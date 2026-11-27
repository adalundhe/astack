"""Separated offline oracle for `vectored-review-planted-bugs`."""
from __future__ import annotations

from pathlib import Path

_REPRO_BUG1_COUPON = '''from src.pricing import apply_coupon


def main() -> None:
    try:
        total = apply_coupon(1000, 150)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for coupon_pct=150, got {total!r}")


if __name__ == "__main__":
    main()
'''

_REPRO_BUG2_DUPLICATE_SKU = '''from src.inventory import Inventory


def main() -> None:
    inv = Inventory({"sku-a": 3})
    try:
        inv.reserve_batch([("sku-a", 2), ("sku-a", 2)])
    except ValueError:
        assert inv.available("sku-a") == 3, f"stock mutated on failed batch: {inv.available('sku-a')}"
        return
    raise AssertionError(
        f"duplicate SKU batch oversold stock; remaining={inv.available('sku-a')}"
    )


if __name__ == "__main__":
    main()
'''

_REPRO_BUG3_SPLIT_LOCK = '''import threading
import time

from src.inventory import Inventory


class YieldingLock:
    def __init__(self) -> None:
        self._inner = threading.Lock()

    def __enter__(self):
        self._inner.acquire()
        return self

    def __exit__(self, *args):
        self._inner.release()
        time.sleep(0.005)


def main() -> None:
    inv = Inventory({"sku-a": 1})
    inv._lock = YieldingLock()
    barrier = threading.Barrier(2)
    succeeded = [0]
    guard = threading.Lock()

    def worker() -> None:
        barrier.wait()
        try:
            inv.reserve_batch([("sku-a", 1)])
            with guard:
                succeeded[0] += 1
        except ValueError:
            pass

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert inv.available("sku-a") >= 0, f"inventory went negative: {inv.available('sku-a')}"
    assert succeeded[0] == 1, f"expected 1 successful reservation, got {succeeded[0]}"


if __name__ == "__main__":
    main()
'''

_REPRO_BUG4_WAL_SEAM = '''import tempfile
from pathlib import Path

from src.inventory import Inventory
from src.models import LineItem
from src.service import OrderService


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        wal = Path(td) / "orders.wal"
        svc = OrderService(Inventory({"sku-a": 5}), wal)
        order = svc.checkout("tenant-a", "req-1", [LineItem("sku-a", 1, 500)])

        replayed = OrderService(Inventory({"sku-a": 5}), wal)
        assert replayed.status_of(order.order_id) == "paid"
        assert replayed.total_revenue() == 500


if __name__ == "__main__":
    main()
'''

_REPRO_BUG5_CACHE_POISON = '''import tempfile
from pathlib import Path

from src.inventory import Inventory
from src.models import LineItem
from src.service import OrderService


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        wal = Path(td) / "orders.wal"
        svc = OrderService(Inventory({"sku-a": 5}), wal)
        svc.checkout("tenant-a", "req-1", [LineItem("sku-a", 1, 500)])
        try:
            svc.refund_order("ord-missing")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for unknown order refund")

        assert svc.status_of("ord-missing") is None, (
            f"status cache poisoned with {svc.status_of('ord-missing')!r}"
        )
        assert svc.total_revenue() == 500, f"revenue cache corrupted: {svc.total_revenue()}"


if __name__ == "__main__":
    main()
'''


def apply(ws: Path) -> dict[str, object]:
    repros = ws / "program" / "repros"
    repros.mkdir(parents=True, exist_ok=True)
    (repros / "repro_bug1_coupon_gt_100.py").write_text(_REPRO_BUG1_COUPON, encoding="utf-8")
    (repros / "repro_bug2_duplicate_sku_batch.py").write_text(_REPRO_BUG2_DUPLICATE_SKU, encoding="utf-8")
    (repros / "repro_bug3_split_lock_race.py").write_text(_REPRO_BUG3_SPLIT_LOCK, encoding="utf-8")
    (repros / "repro_bug4_wal_pipe_delimiter_seam.py").write_text(_REPRO_BUG4_WAL_SEAM, encoding="utf-8")
    (repros / "repro_bug5_refund_cache_poisoning.py").write_text(_REPRO_BUG5_CACHE_POISON, encoding="utf-8")

    return {
        "final_text": (
            "VERDICT: BLOCKED (`repo/` left untouched).\n\n"
            "Blocking findings:\n"
            "1. **Coupon over 100% produces negative totals (`src/pricing.py:apply_coupon`)**: rejects "
            "`coupon_pct < 0` but allows `coupon_pct > 100`. Repro: `program/repros/repro_bug1_coupon_gt_100.py`.\n"
            "2. **Repeated SKU oversell in batch (`src/inventory.py:reserve_batch`)**: validates each line "
            "independently instead of aggregating quantities per SKU. Repro: "
            "`program/repros/repro_bug2_duplicate_sku_batch.py`.\n"
            "3. **Split-lock oversell race (`src/inventory.py:reserve_batch`)**: releases `self._lock` between "
            "stock check and deduction, permitting concurrent oversell. Repro: "
            "`program/repros/repro_bug3_split_lock_race.py`.\n"
            "4. **Cross-file WAL delimiter collision (`src/service.py` + `src/journal.py`)**: `OrderService` "
            "builds `idem_key = f\"{tenant_id}|{client_key}\"` while `OrderJournal` serializes pipe-delimited "
            "lines and replays with `line.split(\"|\", 3)`, breaking restart replay. Repro: "
            "`program/repros/repro_bug4_wal_pipe_delimiter_seam.py`.\n"
            "5. **Refund cache poisoning before journal validation (`src/service.py:refund_order`)**: mutates "
            "`_status_cache` and `_revenue_cache` before `append_refund` validates and persists the refund. "
            "Repro: `program/repros/repro_bug5_refund_cache_poisoning.py`.\n\n"
            "Minor nit: redundant `# compute subtotal` comment in `src/pricing.py`. Verified "
            "`OrderJournal.rotate_snapshot` uses atomic `os.replace` under the service lock (no defect).\n"
        ),
        "events": [],
    }
