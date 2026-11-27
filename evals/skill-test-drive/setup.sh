#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/todo_cli.py <<'EOF'
#!/usr/bin/env python3
"""Minimal file-backed Todo CLI application."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_state(db_path: Path) -> dict[str, object]:
    if not db_path.is_file():
        return {"next_id": 1, "items": {}}
    return json.loads(db_path.read_text(encoding="utf-8"))


def _save_state(db_path: Path, state: dict[str, object]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_add(db_path: Path, title: str) -> int:
    clean = title.strip()
    if not clean:
        print("error: todo title must not be empty", file=sys.stderr)
        return 2
    state = _load_state(db_path)
    next_id = int(state["next_id"])
    items = state["items"]
    assert isinstance(items, dict)
    items[str(next_id)] = {"id": next_id, "title": clean, "done": False}
    state["next_id"] = next_id + 1
    _save_state(db_path, state)
    print(f"added #{next_id}: {clean}")
    return 0


def cmd_list(db_path: Path) -> int:
    state = _load_state(db_path)
    items = state["items"]
    assert isinstance(items, dict)
    if not items:
        print("(empty)")
        return 0
    for key in sorted(items, key=lambda k: int(k)):
        row = items[key]
        mark = "x" if row["done"] else " "
        print(f"[{mark}] #{row['id']}: {row['title']}")
    return 0


def cmd_complete(db_path: Path, todo_id: int) -> int:
    state = _load_state(db_path)
    items = state["items"]
    assert isinstance(items, dict)
    row = items[str(todo_id)]
    row["done"] = True
    _save_state(db_path, state)
    print(f"completed #{todo_id}: {row['title']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="todo-cli", description="Manage a local JSON todo list.")
    parser.add_argument("--db", default="todos.json", help="Path to JSON storage file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a todo item")
    p_add.add_argument("title", help="Todo title")

    sub.add_parser("list", help="List all todo items")

    p_done = sub.add_parser("complete", help="Mark a todo item complete")
    p_done.add_argument("todo_id", type=int, help="Numeric todo ID")

    args = parser.parse_args(argv)
    db_path = Path(args.db)
    if args.command == "add":
        return cmd_add(db_path, args.title)
    if args.command == "list":
        return cmd_list(db_path)
    if args.command == "complete":
        return cmd_complete(db_path, args.todo_id)
    return 2


if __name__ == "__main__":
    sys.exit(main())
EOF
chmod +x repo/src/todo_cli.py

cat > repo/tests/test_todo_cli.py <<'EOF'
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "src" / "todo_cli.py"


class TodoCliTest(unittest.TestCase):
    def test_add_and_list_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "todos.json"
            add = subprocess.run(
                [sys.executable, "-B", str(CLI), "--db", str(db), "add", "Buy milk"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(add.returncode, 0, add.stderr)
            self.assertIn("#1", add.stdout)

            lst = subprocess.run(
                [sys.executable, "-B", str(CLI), "--db", str(db), "list"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(lst.returncode, 0, lst.stderr)
            self.assertIn("[ ] #1: Buy milk", lst.stdout)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial todo_cli app"
git -C repo rev-parse HEAD > program/base_sha.txt
