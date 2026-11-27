#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/aggregate.py <<'EOF'
"""Transaction aggregation utilities."""
from __future__ import annotations

import random
from typing import Any


def generate_records(count: int, seed: int = 42) -> list[dict[str, Any]]:
    """Generate deterministic transaction records for benchmarking and tests."""
    rng = random.Random(seed)
    accounts = [f"acct-{i:03d}" for i in range(64)]
    records: list[dict[str, Any]] = []
    for idx in range(count):
        records.append(
            {
                "tx_id": f"tx-{idx:06d}",
                "account_id": accounts[rng.randrange(len(accounts))],
                "amount_cents": rng.randint(100, 50_000),
                "kind": "credit" if idx % 3 else "debit",
            }
        )
    return records


def aggregate_transactions(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Aggregate transaction counts, net cents, and max amount per account."""
    summary: dict[str, dict[str, int]] = {}
    for rec in records:
        acct = str(rec["account_id"])
        amt = int(rec["amount_cents"])
        signed = amt if rec.get("kind") == "credit" else -amt
        bucket = summary.get(acct)
        if bucket is None:
            summary[acct] = {"count": 1, "net_cents": signed, "max_cents": amt}
        else:
            bucket["count"] += 1
            bucket["net_cents"] += signed
            if amt > bucket["max_cents"]:
                bucket["max_cents"] = amt
    return summary
EOF

cat > repo/tests/test_aggregate.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aggregate import aggregate_transactions, generate_records


class AggregateTest(unittest.TestCase):
    def test_aggregate_transactions_basic(self):
        rows = [
            {"tx_id": "1", "account_id": "a", "amount_cents": 500, "kind": "credit"},
            {"tx_id": "2", "account_id": "a", "amount_cents": 200, "kind": "debit"},
            {"tx_id": "3", "account_id": "b", "amount_cents": 900, "kind": "credit"},
        ]
        got = aggregate_transactions(rows)
        self.assertEqual(got["a"], {"count": 2, "net_cents": 300, "max_cents": 500})
        self.assertEqual(got["b"], {"count": 1, "net_cents": 900, "max_cents": 900})

    def test_generate_records_deterministic(self):
        self.assertEqual(generate_records(50, seed=7), generate_records(50, seed=7))
EOF

cat > program/bench_ask.md <<'EOF'
# Benchmark Request: Transaction Aggregator Baseline

Before changing `./repo/src/aggregate.py`, establish a reproducible baseline benchmark of `aggregate_transactions`.

Requirements:
- Do not modify any files inside `./repo`.
- Write a standalone Python stdlib script at `program/bench.py` that imports `aggregate_transactions` and `generate_records` from `./repo/src/aggregate.py` using paths resolved relative to the script/workspace.
- Use a fixed seeded dataset (for example `generate_records(5000, seed=42)`) and record the exact `dataset_size`.
- Execute warmup iterations (`warmup_runs >= 2`) before collecting at least 5 measured trials (recommend 10–15 trials so reruns complete in a few seconds).
- Consume and verify the aggregated output (such as an output checksum) on every trial to confirm real work ran.
- Running `python3 -B program/bench.py` offline must run the benchmark and write `program/bench_results.json` containing:
  - `dataset_size` (exact integer record count)
  - `warmup_runs` (integer >= 1)
  - `trials` (integer >= 5) and `trials_ms` (list of per-trial millisecond floats)
  - `median_ms`, `p95_ms`, `mean_ms`, and `stdev_ms`
  - `output_checksum` (non-empty verification digest of the aggregation result)
  - `platform` metadata object (`python_version`, `system`, `machine`, `cpu_count`)
  - `rerun_command`
EOF

git -C repo add .
git -C repo commit -q -m "initial transaction aggregator"
