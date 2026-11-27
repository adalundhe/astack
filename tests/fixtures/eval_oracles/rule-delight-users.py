"""Separated offline oracle for `rule-delight-users`."""
from __future__ import annotations

from pathlib import Path

FIXED_CLI = r'''#!/usr/bin/env python3
"""Simple JSON-backed task tracker CLI with actionable UX and safe defaults."""
from __future__ import annotations

import json
from pathlib import Path
import sys


USAGE = "Usage: taskcli.py [--store PATH] {list | add <title> | done <id> | clean [--all]}"


def load_tasks(store: Path) -> list[dict]:
    if not store.exists():
        return []
    try:
        data = json.loads(store.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Task store {store} is not valid JSON ({exc}). Fix or back up the file before retrying."
        ) from exc
    if not isinstance(data, list):
        raise ValueError(f"Task store {store} must contain a JSON list.")
    return data


def save_tasks(store: Path, tasks: list[dict]) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")


def _extract_store(args: list[str]) -> tuple[Path, list[str]]:
    store = Path(".tasks.json")
    rest: list[str] = []
    idx = 0
    while idx < len(args):
        tok = args[idx]
        if tok == "--store":
            if idx + 1 >= len(args):
                raise ValueError("Missing path after --store. Pass a file path, e.g. --store tasks.json.")
            store = Path(args[idx + 1])
            idx += 2
        elif tok.startswith("--store="):
            store = Path(tok.split("=", 1)[1])
            idx += 1
        else:
            rest.append(tok)
            idx += 1
    return store, rest


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    try:
        store, args = _extract_store(raw_args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if args else 2

    cmd, rest = args[0], args[1:]
    try:
        tasks = load_tasks(store)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if cmd == "list":
        if not tasks:
            print("No tasks yet. Run 'taskcli.py add <title>' to create one.")
            return 0
        for task in tasks:
            mark = "x" if task["done"] else " "
            print(f"[{mark}] {task['id']}: {task['title']}")
        return 0

    if cmd == "add":
        title = " ".join(rest).strip()
        if not title:
            print("Error: missing task title. Run 'taskcli.py add <title>'.", file=sys.stderr)
            return 2
        next_id = max((int(t["id"]) for t in tasks), default=0) + 1
        tasks.append({"id": next_id, "title": title, "done": False})
        save_tasks(store, tasks)
        print(f"Added task #{next_id}: {title}")
        return 0

    if cmd == "done":
        if not rest:
            print(
                "Error: missing task ID. Run 'taskcli.py list' to see task IDs, then 'taskcli.py done <id>'.",
                file=sys.stderr,
            )
            return 2
        try:
            task_id = int(rest[0])
        except ValueError:
            print(
                f"Error: invalid task ID {rest[0]!r} (expected an integer). Run 'taskcli.py list' to see valid IDs.",
                file=sys.stderr,
            )
            return 2
        for task in tasks:
            if task["id"] == task_id:
                task["done"] = True
                save_tasks(store, tasks)
                print(f"Completed task #{task_id}: {task['title']}")
                return 0
        print(
            f"Error: task #{task_id} was not found. Run 'taskcli.py list' to view existing tasks.",
            file=sys.stderr,
        )
        return 1

    if cmd == "clean":
        remove_all = "--all" in rest
        if remove_all:
            removed = len(tasks)
            remaining: list[dict] = []
        else:
            remaining = [t for t in tasks if not t["done"]]
            removed = len(tasks) - len(remaining)
        save_tasks(store, remaining)
        if removed == 0:
            print(f"Nothing to clean ({len(remaining)} open task(s) kept). Pass --all to remove open tasks.")
        else:
            print(f"Removed {removed} task(s); {len(remaining)} open task(s) kept.")
        return 0

    print(f"Error: unknown command {cmd!r}. {USAGE}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''

FIXED_TESTS = r'''import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "src" / "taskcli.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(CLI), *args],
        capture_output=True,
        text=True,
    )


class TaskCliBehaviorTest(unittest.TestCase):
    def test_add_and_list_existing_store(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "tasks.json"
            store.write_text("[]\n", encoding="utf-8")
            add = _run("--store", str(store), "add", "Buy milk")
            self.assertEqual(add.returncode, 0)
            self.assertIn("Buy milk", add.stdout)
            lst = _run("--store", str(store), "list")
            self.assertEqual(lst.returncode, 0)
            self.assertIn("Buy milk", lst.stdout)
            saved = json.loads(store.read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 1)

    def test_empty_state_on_missing_store_prints_guidance(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "missing.json"
            lst = _run("--store", str(store), "list")
            self.assertEqual(lst.returncode, 0)
            self.assertNotIn("Traceback", lst.stderr)
            self.assertIn("No tasks", lst.stdout)
            self.assertIn("add", lst.stdout)

    def test_unknown_and_invalid_ids_give_actionable_errors(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "tasks.json"
            _run("--store", str(store), "add", "First task")
            miss = _run("--store", str(store), "done", "999")
            self.assertEqual(miss.returncode, 1)
            self.assertNotIn("Error 42", miss.stderr)
            self.assertNotIn("Traceback", miss.stderr)
            self.assertIn("999", miss.stderr)
            self.assertIn("list", miss.stderr)

            bad = _run("--store", str(store), "done", "abc")
            self.assertEqual(bad.returncode, 2)
            self.assertNotIn("Traceback", bad.stderr)
            self.assertIn("abc", bad.stderr)

            notitle = _run("--store", str(store), "add")
            self.assertEqual(notitle.returncode, 2)
            self.assertNotIn("Traceback", notitle.stderr)
            self.assertIn("title", notitle.stderr)

    def test_clean_preserves_open_tasks_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "tasks.json"
            _run("--store", str(store), "add", "Done item")
            _run("--store", str(store), "add", "Open item")
            done_res = _run("--store", str(store), "done", "1")
            self.assertEqual(done_res.returncode, 0)
            self.assertIn("Done item", done_res.stdout)

            clean_res = _run("--store", str(store), "clean")
            self.assertEqual(clean_res.returncode, 0)
            self.assertIn("Removed 1", clean_res.stdout)
            remaining = json.loads(store.read_text(encoding="utf-8"))
            self.assertEqual([t["title"] for t in remaining], ["Open item"])


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    """Upgrade taskcli.py UX and add behavior tests."""
    repo = ws / "repo"
    (repo / "src" / "taskcli.py").write_text(FIXED_CLI, encoding="utf-8")
    (repo / "tests" / "test_taskcli.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Updated src/taskcli.py to handle empty/missing stores explicitly, replace 'Error 42' "
            "and raw tracebacks with actionable messages stating what failed and the next command, "
            "print confirmation feedback on add/done/clean, and keep open tasks safe by default "
            "during clean unless --all is passed. Added CLI behavior tests in tests/test_taskcli.py."
        ),
    }
