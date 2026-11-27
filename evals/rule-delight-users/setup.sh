#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/taskcli.py <<'EOF'
#!/usr/bin/env python3
"""Simple JSON-backed task tracker CLI."""
from __future__ import annotations

import json
from pathlib import Path
import sys


def load_tasks(store: Path) -> list[dict]:
    return json.loads(store.read_text(encoding="utf-8"))


def save_tasks(store: Path, tasks: list[dict]) -> None:
    store.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    store = Path(".tasks.json")
    if len(args) >= 2 and args[0] == "--store":
        store = Path(args[1])
        args = args[2:]

    cmd = args[0]
    if cmd == "list":
        tasks = load_tasks(store)
        for task in tasks:
            mark = "x" if task["done"] else " "
            print(f"[{mark}] {task['id']}: {task['title']}")
        return 0

    if cmd == "add":
        title = args[1]
        tasks = load_tasks(store) if store.exists() else []
        next_id = max((t["id"] for t in tasks), default=0) + 1
        tasks.append({"id": next_id, "title": title, "done": False})
        save_tasks(store, tasks)
        return 0

    if cmd == "done":
        task_id = int(args[1])
        tasks = load_tasks(store)
        for task in tasks:
            if task["id"] == task_id:
                task["done"] = True
                save_tasks(store, tasks)
                return 0
        print("Error 42", file=sys.stderr)
        return 1

    if cmd == "clean":
        keep_open = "--keep-open" in args[1:]
        tasks = load_tasks(store)
        remaining = [t for t in tasks if keep_open and not t["done"]]
        save_tasks(store, remaining)
        return 0

    print("Error 42", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
EOF
chmod +x repo/src/taskcli.py

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_taskcli.py <<'EOF'
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "src" / "taskcli.py"


class TaskCliBaselineTest(unittest.TestCase):
    def test_add_and_list_existing_store(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "tasks.json"
            store.write_text("[]\n", encoding="utf-8")
            add = subprocess.run(
                [sys.executable, "-B", str(CLI), "--store", str(store), "add", "Buy milk"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(add.returncode, 0)
            lst = subprocess.run(
                [sys.executable, "-B", str(CLI), "--store", str(store), "list"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(lst.returncode, 0)
            self.assertIn("Buy milk", lst.stdout)
            saved = json.loads(store.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 1)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial task tracker CLI"
git -C repo rev-parse HEAD > program/base_sha.txt
