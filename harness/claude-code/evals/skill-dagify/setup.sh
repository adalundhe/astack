#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/models.py <<'EOF'
"""Frozen shared expense record contract (read-only across feature slices)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpenseRecord:
    record_id: str
    amount_cents: int
    currency: str
    category: str
EOF

cat > repo/src/parser.py <<'EOF'
"""Expense CSV/JSONL parser (stub)."""
EOF

cat > repo/src/validator.py <<'EOF'
"""Expense record validator (stub)."""
EOF

cat > repo/src/storage.py <<'EOF'
"""Atomic JSONL expense storage (stub)."""
EOF

cat > repo/src/cli.py <<'EOF'
"""CLI entrypoint wiring parser, validator, and storage (stub)."""
EOF

cat > repo/tests/test_models.py <<'EOF'
import unittest
from src.models import ExpenseRecord


class ModelsTest(unittest.TestCase):
    def test_expense_record(self):
        rec = ExpenseRecord("e1", 1250, "USD", "travel")
        self.assertEqual(rec.amount_cents, 1250)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial expense pipeline stubs with frozen models contract"

cat > program/spec.md <<'EOF'
# Feature Spec: Expense Ingestion Pipeline

`repo/src/models.py` already defines the frozen `ExpenseRecord(record_id, amount_cents, currency, category)` contract. Do not modify `src/models.py`.

Build four slices across `./repo`:

1. **`src/parser.py`** (`tests/test_parser.py`): Parse CSV and JSONL input streams into `list[ExpenseRecord]`, rejecting malformed rows with line numbers and refusing float dollar strings without exact cent conversion.
2. **`src/validator.py`** (`tests/test_validator.py`): Validate `ExpenseRecord` objects against allowed ISO currencies (`USD`, `EUR`, `GBP`), positive integer `amount_cents`, non-empty `category`, and duplicate `record_id` detection.
3. **`src/storage.py`** (`tests/test_storage.py`): Persist and query `ExpenseRecord` batches in an append-safe JSONL store using temp-file + `os.replace` atomic writes and idempotent deduplication by `record_id`.
4. **`src/cli.py`** (`tests/test_cli.py`): Wire `parser`, `validator`, and `storage` into an `ingest` and `summary` CLI returning exit code 0 on valid batches and non-zero with structured error details on invalid input.

All design decisions are settled. Slice this into a parallelizable execution DAG written to `program/DAG.md`.
EOF
