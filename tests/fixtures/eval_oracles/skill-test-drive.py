"""Separated offline oracle for `skill-test-drive`."""
from __future__ import annotations

import os
from pathlib import Path

FIXED_TODO_CLI = '''#!/usr/bin/env python3
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
    db_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


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
    row = items.get(str(todo_id))
    if row is None:
        print(f"error: todo #{todo_id} not found", file=sys.stderr)
        return 1
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
'''

DRIVER_SCRIPT = '''#!/usr/bin/env python3
"""End-to-end user-flow driver for repo/src/todo_cli.py."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "repo" / "src" / "todo_cli.py"


def run_cli(db: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(CLI), "--db", str(db), *args],
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="drive-todo-") as td:
        db = Path(td) / "todos.json"

        # 1. Doctor / preflight on empty store
        empty = run_cli(db, "list")
        assert empty.returncode == 0 and "(empty)" in empty.stdout, empty.stderr

        # 2. Add flow
        added = run_cli(db, "add", "Draft release notes")
        assert added.returncode == 0 and "#1" in added.stdout, added.stderr

        # 3. List flow
        listed = run_cli(db, "list")
        assert listed.returncode == 0 and "[ ] #1: Draft release notes" in listed.stdout, listed.stdout

        # 4. Complete flow
        done = run_cli(db, "complete", "1")
        assert done.returncode == 0 and "completed #1" in done.stdout, done.stderr
        listed_done = run_cli(db, "list")
        assert listed_done.returncode == 0 and "[x] #1: Draft release notes" in listed_done.stdout, listed_done.stdout

        # 5. Invalid/missing ID flow
        missing = run_cli(db, "complete", "999")
        combined = missing.stdout + missing.stderr
        assert missing.returncode != 0, "expected non-zero exit for missing todo ID"
        assert "Traceback" not in combined and "KeyError" not in combined, combined
        assert "not found" in combined.lower() or "999" in combined, combined

    print("PASS: all todo_cli end-to-end flows verified (add, list, complete, invalid ID)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

UPDATED_TESTS = '''import subprocess
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

    def test_complete_marks_item_done(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "todos.json"
            subprocess.run([sys.executable, "-B", str(CLI), "--db", str(db), "add", "Write tests"], check=True, capture_output=True)
            done = subprocess.run(
                [sys.executable, "-B", str(CLI), "--db", str(db), "complete", "1"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            lst = subprocess.run(
                [sys.executable, "-B", str(CLI), "--db", str(db), "list"],
                capture_output=True,
                text=True,
            )
            self.assertIn("[x] #1: Write tests", lst.stdout)

    def test_complete_missing_id_exits_nonzero_without_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "todos.json"
            proc = subprocess.run(
                [sys.executable, "-B", str(CLI), "--db", str(db), "complete", "999"],
                capture_output=True,
                text=True,
            )
            combined = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn("Traceback", combined)
            self.assertNotIn("KeyError", combined)
            self.assertIn("999", combined)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    """Create executable program/drive-todo.py, fix missing-ID KeyError in todo_cli.py, and add regression tests."""
    repo = ws / "repo"
    cli = repo / "src" / "todo_cli.py"
    cli.write_text(FIXED_TODO_CLI, encoding="utf-8")
    os.chmod(cli, 0o755)

    (repo / "tests" / "test_todo_cli.py").write_text(UPDATED_TESTS, encoding="utf-8")

    driver = ws / "program" / "drive-todo.py"
    driver.write_text(DRIVER_SCRIPT, encoding="utf-8")
    os.chmod(driver, 0o755)

    return {
        "final_text": (
            "Created executable end-to-end driver `program/drive-todo.py` exercising `add`, `list`, `complete`, "
            "and missing-ID flows in an isolated temporary directory. Fixed the uncaught `KeyError` in "
            "`repo/src/todo_cli.py` (`cmd_complete`) so missing IDs print a clear stderr error and exit 1, "
            "added regression unit tests in `repo/tests/test_todo_cli.py`, and proved both the driver script and unittest suite pass."
        ),
    }
