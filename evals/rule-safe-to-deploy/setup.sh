#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/schema.py <<'EOF'
"""SQLite schema setup and v1 -> v2 migration for users."""
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
    """Migrate users table so v2 can store contact_email."""
    conn.execute("ALTER TABLE users RENAME COLUMN email TO contact_email")
    conn.commit()
EOF

cat > repo/src/reader_v1.py <<'EOF'
"""Frozen v1 application queries simulating live pre-change pods and rolled-back releases."""
from __future__ import annotations

import sqlite3


def get_user_v1(conn: sqlite3.Connection, user_id: int) -> dict[str, object] | None:
    row = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "email": row[2]}


def create_user_v1(conn: sqlite3.Connection, name: str, email: str) -> int:
    cur = conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    return int(cur.lastrowid)
EOF

cat > repo/src/service_v2.py <<'EOF'
"""New v2 service using contact_email."""
from __future__ import annotations

import sqlite3


def get_user_v2(conn: sqlite3.Connection, user_id: int) -> dict[str, object] | None:
    row = conn.execute(
        "SELECT id, name, contact_email FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "contact_email": row[2]}


def create_user_v2(conn: sqlite3.Connection, name: str, contact_email: str) -> int:
    cur = conn.execute(
        "INSERT INTO users (name, contact_email) VALUES (?, ?)",
        (name, contact_email),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_contact_email_v2(conn: sqlite3.Connection, user_id: int, contact_email: str) -> None:
    conn.execute(
        "UPDATE users SET contact_email = ? WHERE id = ?",
        (contact_email, user_id),
    )
    conn.commit()
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_migration.py <<'EOF'
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from schema import init_v1_db, migrate_to_v2
from service_v2 import create_user_v2, get_user_v2, update_contact_email_v2


class MigrationBaselineTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial destructive migration"
git -C repo rev-parse HEAD > program/base_sha.txt
