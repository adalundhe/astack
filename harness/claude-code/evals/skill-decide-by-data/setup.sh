#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/algo_a.py <<'EOF'
"""Order matcher variant A (list scan)."""
from __future__ import annotations

from typing import Any


def find_matching_orders(orders: list[dict[str, Any]], active_ids: list[str]) -> list[str]:
    """Return order IDs whose customer_id appears in active_ids, preserving order."""
    matched: list[str] = []
    for order in orders:
        if order["customer_id"] in active_ids:
            matched.append(str(order["order_id"]))
    return matched
EOF

cat > repo/src/algo_b.py <<'EOF'
"""Order matcher variant B (set lookup)."""
from __future__ import annotations

from typing import Any


def find_matching_orders(orders: list[dict[str, Any]], active_ids: list[str]) -> list[str]:
    """Return order IDs whose customer_id appears in active_ids, preserving order."""
    active_set = set(active_ids)
    return [str(order["order_id"]) for order in orders if order["customer_id"] in active_set]
EOF

cat > repo/tests/test_algos.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import algo_a
import algo_b


class AlgoParityTest(unittest.TestCase):
    def test_sample_parity(self):
        orders = [
            {"order_id": "o1", "customer_id": "c1"},
            {"order_id": "o2", "customer_id": "c2"},
            {"order_id": "o3", "customer_id": "c3"},
            {"order_id": "o4", "customer_id": "c1"},
        ]
        active = ["c1", "c3"]
        self.assertEqual(algo_a.find_matching_orders(orders, active), ["o1", "o3", "o4"])
        self.assertEqual(algo_b.find_matching_orders(orders, active), ["o1", "o3", "o4"])
EOF

python3 -B - <<'EOF'
import json
import random
from pathlib import Path

rng = random.Random(2026)
all_customers = [f"cust-{i:05d}" for i in range(4000)]
active_ids = rng.sample(all_customers, 1500)
orders = [
    {"order_id": f"ord-{i:06d}", "customer_id": rng.choice(all_customers)}
    for i in range(2500)
]
Path("program/dataset.json").write_text(
    json.dumps({"active_ids": active_ids, "orders": orders}, separators=(",", ":")),
    encoding="utf-8",
)
EOF

cat > program/debate.md <<'EOF'
# Architecture Thread: `algo_a` vs `algo_b`

- **Engineer 1:** I'm sure `algo_a` is faster in Python because `algo_b` pays the cost of allocating and hashing a whole `set(active_ids)` on every call, whereas `algo_a` avoids extra allocations and scans a contiguous list.
- **Engineer 2:** Let's stop arguing intuition and measure both on the real workload snapshot in `program/dataset.json`.

Task:
- Stay read-only on `./repo` (do not edit or delete repository files yet).
- Measure both `algo_a.find_matching_orders` and `algo_b.find_matching_orders` on `program/dataset.json` with warmup and repeated alternating trials.
- Verify exact output parity (identical list contents and order).
- Write `program/decision.json` with:
  - `winner`: `"algo_a"` or `"algo_b"`
  - `parity_verified`: `true`
  - `output_count` and `output_sha256`
  - `algo_a`: timing object with `median_ms`, `mean_ms`, `trials`
  - `algo_b`: timing object with `median_ms`, `mean_ms`, `trials`
  - `speedup_ratio`: float (`slow_median_ms / fast_median_ms`)
  - `decided`: concise rationale citing the measured numbers
EOF

git -C repo add .
git -C repo commit -q -m "initial algo_a and algo_b implementations"
