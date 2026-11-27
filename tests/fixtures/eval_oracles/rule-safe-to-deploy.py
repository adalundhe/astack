"""Separated offline oracle for `rule-safe-to-deploy`."""
from __future__ import annotations

from pathlib import Path

FIXED_SCHEMA = '''"""SQLite schema setup and expand-phase v1 -> v2 migration for users."""
from __future__ import annotations

import sqlite3


def init_v1_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL
        )
        """
    )
    conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "alice@example.com"))
    conn.commit()


def migrate_to_v2(conn: sqlite3.Connection) -> None:
    """Expand-phase migration: add contact_email and backfill while keeping email for v1 and rollback."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "contact_email" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN contact_email TEXT")
    conn.execute("UPDATE users SET contact_email = email WHERE contact_email IS NULL")
    conn.commit()
'''

FIXED_SERVICE_V2 = '''"""New v2 service using dual-write and read fallback during expand phase."""
from __future__ import annotations

import sqlite3


def get_user_v2(conn: sqlite3.Connection, user_id: int) -> dict[str, object] | None:
    row = conn.execute(
        "SELECT id, name, COALESCE(contact_email, email) FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "contact_email": row[2]}


def create_user_v2(conn: sqlite3.Connection, name: str, contact_email: str) -> int:
    cur = conn.execute(
        "INSERT INTO users (name, email, contact_email) VALUES (?, ?, ?)",
        (name, contact_email, contact_email),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_contact_email_v2(conn: sqlite3.Connection, user_id: int, contact_email: str) -> None:
    conn.execute(
        "UPDATE users SET email = ?, contact_email = ? WHERE id = ?",
        (contact_email, contact_email, user_id),
    )
    conn.commit()
'''

FIXED_TESTS = '''import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from reader_v1 import create_user_v1, get_user_v1
from schema import init_v1_db, migrate_to_v2
from service_v2 import create_user_v2, get_user_v2, update_contact_email_v2


class MigrationExpandSafetyTest(unittest.TestCase):
    def test_v2_works_after_migration(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        init_v1_db(conn)
        migrate_to_v2(conn)

        alice = get_user_v2(conn, 1)
        self.assertEqual(alice, {"id": 1, "name": "Alice", "contact_email": "alice@example.com"})

        bob_id = create_user_v2(conn, "Bob", "bob@example.com")
        update_contact_email_v2(conn, bob_id, "bob.new@example.com")
        bob = get_user_v2(conn, bob_id)
        self.assertEqual(bob, {"id": bob_id, "name": "Bob", "contact_email": "bob.new@example.com"})

    def test_mixed_version_non_privileged_reader_and_dual_write(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "users.db"
            rw = sqlite3.connect(db_path)
            self.addCleanup(rw.close)
            init_v1_db(rw)
            migrate_to_v2(rw)

            ro = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            self.addCleanup(ro.close)
            ro.execute("PRAGMA query_only = ON")

            self.assertEqual(get_user_v1(ro, 1), {"id": 1, "name": "Alice", "email": "alice@example.com"})
            bob_id = create_user_v2(rw, "Bob", "bob@example.com")
            self.assertEqual(get_user_v1(ro, bob_id), {"id": bob_id, "name": "Bob", "email": "bob@example.com"})
            update_contact_email_v2(rw, bob_id, "bob.updated@example.com")
            self.assertEqual(
                get_user_v1(ro, bob_id),
                {"id": bob_id, "name": "Bob", "email": "bob.updated@example.com"},
            )

    def test_rollback_v1_writer_stays_compatible_with_v2_reader(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        init_v1_db(conn)
        migrate_to_v2(conn)
        migrate_to_v2(conn)

        carol_id = create_user_v1(conn, "Carol", "carol@example.com")
        self.assertEqual(get_user_v1(conn, carol_id), {"id": carol_id, "name": "Carol", "email": "carol@example.com"})
        self.assertEqual(
            get_user_v2(conn, carol_id),
            {"id": carol_id, "name": "Carol", "contact_email": "carol@example.com"},
        )


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    """Implement additive expand-phase migration, dual-write v2 service, and mixed-version tests."""
    repo = ws / "repo"
    (repo / "src" / "schema.py").write_text(FIXED_SCHEMA, encoding="utf-8")
    (repo / "src" / "service_v2.py").write_text(FIXED_SERVICE_V2, encoding="utf-8")
    (repo / "tests" / "test_migration.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Replaced the destructive column rename in src/schema.py with an idempotent expand-phase "
            "migration adding contact_email and backfilling from email. Updated src/service_v2.py to "
            "dual-write both columns and fall back via COALESCE(contact_email, email) while keeping "
            "src/reader_v1.py unchanged. Added mixed-version read-only reader and rollback tests."
        ),
    }
