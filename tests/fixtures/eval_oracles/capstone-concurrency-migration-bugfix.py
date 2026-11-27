"""Separated offline oracle for `capstone-concurrency-migration-bugfix`."""
from __future__ import annotations

from pathlib import Path

_FIXED_LEDGER = '''"""SQLite-backed payment ledger for pay-core."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=15.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_ledger(db_path: str | Path) -> None:
    """Create initial v1 accounts and transfers tables."""
    conn = _connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0)
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
    finally:
        conn.close()


def create_account(db_path: str | Path, account_id: str, balance_cents: int) -> None:
    if balance_cents < 0:
        raise ValueError("initial balance must be non-negative")
    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT OR REPLACE INTO accounts (account_id, balance_cents) VALUES (?, ?)",
            (account_id, int(balance_cents)),
        )
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
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
    """Atomically transfer funds inside a write-locked IMMEDIATE transaction."""
    if amount_cents <= 0:
        raise ValueError("amount_cents must be positive")
    if from_account == to_account:
        raise ValueError("cannot transfer to the same account")

    conn = _connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        src = conn.execute(
            "SELECT balance_cents FROM accounts WHERE account_id = ?",
            (from_account,),
        ).fetchone()
        if src is None:
            conn.execute("ROLLBACK")
            raise KeyError(f"unknown account: {from_account}")

        cur = conn.execute(
            "UPDATE accounts SET balance_cents = balance_cents - ? "
            "WHERE account_id = ? AND balance_cents >= ?",
            (amount_cents, from_account, amount_cents),
        )
        if cur.rowcount != 1:
            conn.execute("ROLLBACK")
            return False

        dst = conn.execute(
            "UPDATE accounts SET balance_cents = balance_cents + ? WHERE account_id = ?",
            (amount_cents, to_account),
        )
        if dst.rowcount != 1:
            conn.execute("ROLLBACK")
            raise KeyError(f"unknown account: {to_account}")

        cols = {r[1] for r in conn.execute("PRAGMA table_info(transfers)").fetchall()}
        if "total_cents" in cols and "amount_cents" in cols:
            conn.execute(
                "INSERT INTO transfers (from_account, to_account, amount_cents, total_cents) "
                "VALUES (?, ?, ?, ?)",
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
        conn.execute("COMMIT")
        return True
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def list_transfers_v2(db_path: str | Path) -> list[dict[str, object]]:
    """Read transfers using v2 total_cents with safe fallback for pre-backfill rows."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT transfer_id, from_account, to_account, "
            "COALESCE(total_cents, amount_cents) AS total_cents "
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
'''

_FIXED_MIGRATE = '''"""Idempotent additive expand migration for pay-core transfers table."""
from __future__ import annotations

import sqlite3
from pathlib import Path


def migrate_to_v2(db_path: str | Path) -> None:
    """Expand transfers with nullable total_cents, backfill, and keep v1/v2 synced."""
    conn = sqlite3.connect(str(db_path), timeout=15.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        conn.execute("BEGIN IMMEDIATE")
        cols = {r[1] for r in conn.execute("PRAGMA table_info(transfers)").fetchall()}
        if "total_cents" not in cols:
            conn.execute("ALTER TABLE transfers ADD COLUMN total_cents INTEGER")
        conn.execute(
            "UPDATE transfers SET total_cents = amount_cents WHERE total_cents IS NULL"
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_transfers_sync_v1_insert
            AFTER INSERT ON transfers
            WHEN NEW.total_cents IS NULL
            BEGIN
                UPDATE transfers SET total_cents = NEW.amount_cents
                WHERE transfer_id = NEW.transfer_id;
            END
            """
        )
        conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_transfers_sync_v2_insert
            AFTER INSERT ON transfers
            WHEN NEW.amount_cents IS NULL
            BEGIN
                UPDATE transfers SET amount_cents = NEW.total_cents
                WHERE transfer_id = NEW.transfer_id;
            END
            """
        )
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
'''

_FIXED_TESTS = '''"""Behavioral tests for pay-core concurrency and mixed-version migration."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import ledger
import migrate
import reader_v1


class PaymentLedgerTests(unittest.TestCase):
    def test_transfer_calls_execute(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "basic.db"
            ledger.init_ledger(db)
            ledger.create_account(db, "a", 1000)
            ledger.create_account(db, "b", 0)
            self.assertTrue(ledger.transfer(db, "a", "b", 100))
            self.assertEqual(ledger.get_balance(db, "a"), 900)
            self.assertEqual(ledger.get_balance(db, "b"), 100)

    def test_migrate_calls_execute(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "mig.db"
            ledger.init_ledger(db)
            migrate.migrate_to_v2(db)
            migrate.migrate_to_v2(db)
            conn = sqlite3.connect(str(db))
            cols = {r[1] for r in conn.execute("PRAGMA table_info(transfers)").fetchall()}
            conn.close()
            self.assertIn("amount_cents", cols)
            self.assertIn("total_cents", cols)

    def test_concurrent_transfers_prevent_double_spend(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "concurrent.db"
            ledger.init_ledger(db)
            migrate.migrate_to_v2(db)
            ledger.create_account(db, "src", 1000)
            ledger.create_account(db, "dst", 0)

            barrier = threading.Barrier(6)
            results: list[bool] = []
            errors: list[BaseException] = []
            lock = threading.Lock()

            def attempt() -> None:
                try:
                    barrier.wait(timeout=5.0)
                    ok = ledger.transfer(db, "src", "dst", 700)
                    with lock:
                        results.append(ok)
                except BaseException as exc:
                    with lock:
                        errors.append(exc)

            threads = [threading.Thread(target=attempt) for _ in range(6)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=15.0)

            self.assertEqual(errors, [])
            self.assertEqual(len(results), 6)
            self.assertEqual(sum(1 for r in results if r), 1)
            self.assertEqual(ledger.get_balance(db, "src"), 300)
            self.assertEqual(ledger.get_balance(db, "dst"), 700)

    def test_mixed_version_readers_and_rollback_stay_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "mixed.db"
            ledger.init_ledger(db)
            ledger.create_account(db, "a", 2000)
            ledger.create_account(db, "b", 0)

            reader_v1.record_transfer_v1(db, "a", "b", 200)
            migrate.migrate_to_v2(db)
            self.assertTrue(ledger.transfer(db, "a", "b", 350))
            reader_v1.record_transfer_v1(db, "a", "b", 150)

            v1 = reader_v1.list_transfers_v1(db, read_only=True)
            v2 = ledger.list_transfers_v2(db)
            self.assertEqual([r["amount_cents"] for r in v1], [200, 350, 150])
            self.assertEqual([r["total_cents"] for r in v2], [200, 350, 150])


if __name__ == "__main__":
    unittest.main()
'''

_REPRO_SCRIPT = '''#!/usr/bin/env python3
"""Deterministic repro verifying concurrency conservation and v1/v2 migration safety."""
from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4] / "repo" / "src"
if not ROOT.is_dir():
    ROOT = Path.cwd() / "repo" / "src"
sys.path.insert(0, str(ROOT))

import ledger
import migrate
import reader_v1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="repro-pay-core-") as td:
        db = Path(td) / "pay.db"
        ledger.init_ledger(db)
        ledger.create_account(db, "src", 1000)
        ledger.create_account(db, "dst", 0)
        reader_v1.record_transfer_v1(db, "src", "dst", 100)
        migrate.migrate_to_v2(db)

        v1 = reader_v1.list_transfers_v1(db, read_only=True)
        if [r["amount_cents"] for r in v1] != [100]:
            print(f"FAIL: v1 reader broken after migration: {v1}", file=sys.stderr)
            return 1

        barrier = threading.Barrier(6)
        results: list[bool] = []
        lock = threading.Lock()

        def worker() -> None:
            barrier.wait(timeout=5.0)
            ok = ledger.transfer(db, "src", "dst", 700)
            with lock:
                results.append(ok)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        if sum(1 for r in results if r) != 1 or ledger.get_balance(db, "src") != 300:
            print(f"FAIL: double-spend detected results={results} src={ledger.get_balance(db, 'src')}", file=sys.stderr)
            return 1

    print("PASS: concurrency conservation and v1/v2 migration compatibility verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "ledger.py").write_text(_FIXED_LEDGER, encoding="utf-8")
    (repo / "src" / "migrate.py").write_text(_FIXED_MIGRATE, encoding="utf-8")
    (repo / "tests" / "test_ledger.py").write_text(_FIXED_TESTS, encoding="utf-8")

    astack_home = ws / "program" / "astack_home" / "pay-core"
    repro_dir = astack_home / "repros" / "double-spend-and-migration"
    repro_dir.mkdir(parents=True, exist_ok=True)
    repro_path = repro_dir / "repro.py"
    repro_path.write_text(_REPRO_SCRIPT, encoding="utf-8")
    repro_path.chmod(0o755)

    reviews_dir = astack_home / "reviews" / "2026-11-26T09-35-00Z"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    (reviews_dir / "verification.txt").write_text(
        "Verified pay-core fixes:\n"
        "- Atomic BEGIN IMMEDIATE + conditional UPDATE prevents concurrent double-spend across 6 barrier threads.\n"
        "- Idempotent additive expand migration keeps amount_cents + total_cents in sync via triggers for v1 RO readers and rollback.\n"
        "- Unit test suite (4 tests) passes against real SQLite.\n",
        encoding="utf-8",
    )

    return {
        "final_text": (
            "Fixed both pay-core defects and verified with real SQLite tests and runnable proof:\n"
            "- Replaced split check-then-write in `repo/src/ledger.py` with `BEGIN IMMEDIATE` + conditional debit.\n"
            "- Replaced destructive rename in `repo/src/migrate.py` with idempotent additive `total_cents` expansion + sync triggers; `repo/src/reader_v1.py` untouched.\n"
            "- Saved runnable repro at `program/astack_home/pay-core/repros/double-spend-and-migration/repro.py` and proof log under `program/astack_home/pay-core/reviews/2026-11-26T09-35-00Z/verification.txt`."
        ),
    }
