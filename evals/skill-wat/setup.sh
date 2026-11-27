#!/usr/bin/env bash
set -euo pipefail

mkdir -p program repo/src

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/orders.py <<'EOF'
"""Order checkout writer (illustrative target referenced by status draft)."""
from __future__ import annotations


def charge_order(orders: dict[str, dict], order_id: str, amount_cents: int) -> dict:
    # Unsynchronized read-modify-write against shared orders table state.
    existing = orders.get(order_id)
    if existing and existing.get("status") == "paid":
        return existing
    record = {"order_id": order_id, "amount_cents": amount_cents, "status": "paid"}
    orders[order_id] = record
    return record
EOF

git -C repo add .
git -C repo commit -q -m "add orders checkout handler"

cat > program/jargon_draft.md <<'EOF'
# Status Report — LANE-42 (worktree /tmp/wt-8841)

## Process & Harness State
Per settings.json default, reviewer_pool dispatched two passes against astack-review-ledger and recorded coverage-map.md metrics (n1=2/n2=2/m=1). The automated ledger subsequently entered STOPPED (budget) and hit POOL EXHAUSTED after commit a91c4ef was checked under [rule: no-shared-writes].

## Open Items (Telemetry & Notes)
- Staging soak run recorded p95 checkout latency of 180ms across 12 concurrent retry requests, with 3 of 12 producing duplicate charge rows.
- Worktree synchronization for LANE-42 finished prior to ledger halt; no additional model roster slots remained in reviewer_pool.
- Bottom note from staging run: orders table race condition causes double-charge on concurrent retries; do not ship release v2.4 until a row lock or unique idempotency constraint is added in src/orders.py and re-tested.
EOF
