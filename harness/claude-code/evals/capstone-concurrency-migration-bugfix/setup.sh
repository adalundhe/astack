#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home/pay-core repo/src repo/tests

cat > program/brief.md <<'EOF'
# Incident & Migration Brief — `pay-core`

Project name: `pay-core`
Workspace artifacts home: `program/astack_home/pay-core/`

## Reported Production Failures

1. **Concurrent double-spend (`./repo/src/ledger.py`):**
   When multiple threads submit concurrent transfers from the same source account, more than one transfer can pass the balance check before any debit commits, driving `balance_cents` negative and creating money out of thin air.
2. **Rolling-deploy & rollback breakage (`./repo/src/migrate.py`):**
   The `v2` schema migration introduces `total_cents` on `transfers`, but currently renames `amount_cents` directly. During canary rollouts and rollbacks, already-deployed v1 instances (`./repo/src/reader_v1.py`) crash with `OperationalError: no such column: amount_cents`, and rolled-back v1 writers stop populating `total_cents`.
3. **False confidence from mocked tests (`./repo/tests/test_ledger.py`):**
   Existing tests mock `sqlite3.connect` and pass even though both production bugs reproduce immediately against a real SQLite database.

## Constraints & Public Interface

- Do **not** modify `./repo/src/reader_v1.py`; it represents the already-deployed v1 binary running during rollout and rollback.
- Preserve public signatures in `./repo/src/ledger.py` (`init_ledger`, `create_account`, `get_balance`, `transfer`, `list_transfers_v2`) and `./repo/src/migrate.py` (`migrate_to_v2`).
- Both v1 readers (including non-privileged read-only connections) and v2 readers must see accurate transfer amounts across pre-migration rows, v2 writes, and rolled-back v1 writes.
- Persist a runnable reproduction script under `program/astack_home/pay-core/repros/` and raw verification/review proof under `program/astack_home/pay-core/reviews/`.
EOF

cat > repo/src/__init__.py <<'EOF'
"""pay-core SQLite payment ledger package."""
EOF

cat > repo/src/ledger.py <<'EOF'
"""SQLite-backed payment ledger for pay-core."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_ledger(db_path: str | Path) -> None:
    """Create initial v1 accounts and transfers tables."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                balance_cents INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transfers (
                transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_account TEXT NOT NULL,
                to_account TEXT NOT NULL,
                amount_cents INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_account(db_path: str | Path, account_id: str, balance_cents: int) -> None:
    if balance_cents < 0:
        raise ValueError("initial balance must be non-negative")
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO accounts (account_id, balance_cents) VALUES (?, ?)",
            (account_id, int(balance_cents)),
        )
        conn.commit()
    finally:
        conn.close()


def get_balance(db_path: str | Path, account_id: str) -> int:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT balance_cents FROM accounts WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown account: {account_id}")
        return int(row["balance_cents"])
    finally:
        conn.close()


def transfer(
    db_path: str | Path,
    from_account: str,
    to_account: str,
    amount_cents: int,
) -> bool:
    """Transfer funds between accounts (BUGGY: split check-then-write race)."""
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if from_account == to_account:
        raise ValueError("cannot transfer to the same account")

    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT balance_cents FROM accounts WHERE account_id = ?",
            (from_account,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown account: {from_account}")
        if int(row["balance_cents"]) < amount_cents:
            return False

        # Simulates validation/scheduling window between check and debit.
        time.sleep(0.02)

        cols = {r[1] for r in conn.execute("PRAGMA table_info(transfers)").fetchall()}
        conn.execute(
            "UPDATE accounts SET balance_cents = balance_cents - ? WHERE account_id = ?",
            (amount_cents, from_account),
        )
        conn.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? WHERE account_id = ?",
            (amount_cents, to_account),
        )
        if "total_cents" in cols and "amount_cents" in cols:
            conn.execute(
                "INSERT INTO transfers (from_account, to_account, amount_cents, total_cents) VALUES (?, ?, ?, ?)",
                (from_account, to_account, amount_cents, amount_cents),
            )
        elif "total_cents" in cols:
            conn.execute(
                "INSERT INTO transfers (from_account, to_account, total_cents) VALUES (?, ?, ?)",
                (from_account, to_account, amount_cents),
            )
        else:
            conn.execute(
                "INSERT INTO transfers (from_account, to_account, amount_cents) VALUES (?, ?, ?)",
                (from_account, to_account, amount_cents),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def list_transfers_v2(db_path: str | Path) -> list[dict[str, object]]:
    """Read transfers using the v2 total_cents schema."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT transfer_id, from_account, to_account, total_cents "
            "FROM transfers ORDER BY transfer_id"
        ).fetchall()
        return [
            {
                "transfer_id": int(r["transfer_id"]),
                "from_account": str(r["from_account"]),
                "to_account": str(r["to_account"]),
                "total_cents": int(r["total_cents"]),
            }
            for r in rows
        ]
    finally:
        conn.close()
EOF

cat > repo/src/migrate.py <<'EOF'
"""Schema migration for pay-core transfers table."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def migrate_to_v2(db_path: str | Path) -> None:
    """BUGGY: destructive direct column rename breaks v1 readers and rollback."""
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    try:
        conn.execute("ALTER TABLE transfers RENAME COLUMN amount_cents TO total_cents")
        conn.commit()
    finally:
        conn.close()
EOF

cat > repo/src/reader_v1.py <<'EOF'
"""Frozen pre-change v1 reader and writer running during canary deploy and rollback.

Do not modify this module: it represents already-deployed v1 instances.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def list_transfers_v1(db_path: str | Path, *, read_only: bool = True) -> list[dict[str, object]]:
    """Read transfers using legacy v1 amount_cents column."""
    if read_only:
        conn = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = ON")
    else:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT transfer_id, from_account, to_account, amount_cents "
            "FROM transfers ORDER BY transfer_id"
        ).fetchall()
        return [
            {
                "transfer_id": int(r["transfer_id"]),
                "from_account": str(r["from_account"]),
                "to_account": str(r["to_account"]),
                "amount_cents": int(r["amount_cents"]),
            }
            for r in rows
        ]
    finally:
        conn.close()


def record_transfer_v1(
    db_path: str | Path,
    from_account: str,
    to_account: str,
    amount_cents: int,
) -> int:
    """Legacy v1 writer inserting only amount_cents (simulates rollback or mixed-version write)."""
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    try:
        cur = conn.execute(
            "INSERT INTO transfers (from_account, to_account, amount_cents) VALUES (?, ?, ?)",
            (from_account, to_account, int(amount_cents)),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()
EOF

cat > repo/tests/test_ledger.py <<'EOF'
"""Weak mocked tests that hide both the double-spend race and destructive migration."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ledger
import migrate


class WeakMockedLedgerTests(unittest.TestCase):
    def test_transfer_calls_execute(self) -> None:
        fake_conn = MagicMock()
        fake_conn.execute.return_value.fetchone.return_value = {"balance_cents": 1000}
        fake_conn.execute.return_value.fetchall.return_value = [(0, "amount_cents")]
        with patch("ledger.sqlite3.connect", return_value=fake_conn):
            ok = ledger.transfer("ignored.db", "a", "b", 100)
        self.assertTrue(ok)
        self.assertTrue(fake_conn.commit.called)

    def test_migrate_calls_execute(self) -> None:
        fake_conn = MagicMock()
        with patch("migrate.sqlite3.connect", return_value=fake_conn):
            migrate.migrate_to_v2("ignored.db")
        self.assertTrue(fake_conn.commit.called)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo init -q -b main
git -C repo config user.name "Eval Fixture"
git -C repo config user.email "eval@example.invalid"
git -C repo add .
git -C repo commit -q -m "chore: initial pay-core ledger with concurrency and migration defects"
git -C repo rev-parse HEAD > program/base_sha.txt
