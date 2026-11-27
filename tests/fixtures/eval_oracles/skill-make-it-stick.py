"""Separated offline oracle for `skill-make-it-stick`."""
from __future__ import annotations

from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Fix naive datetime.now() in src/events.py and add an AST structural guard test for all src/*.py."""
    repo = ws / "repo"
    (repo / "src" / "events.py").write_text(
        '"""Event envelope builder."""\n'
        "from __future__ import annotations\n\n"
        "from datetime import datetime, timezone\n\n\n"
        "def record_event(kind: str, payload: dict) -> dict:\n"
        '    """Build an event envelope with a UTC timestamp."""\n'
        "    return {\n"
        '        "kind": kind,\n'
        '        "payload": dict(payload),\n'
        '        "occurred_at": datetime.now(timezone.utc).isoformat(),\n'
        "    }\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_events.py").write_text(
        "import sys\n"
        "import unittest\n"
        "from datetime import datetime, timedelta\n"
        "from pathlib import Path\n\n"
        'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))\n'
        "from events import record_event\n\n\n"
        "class EventsTest(unittest.TestCase):\n"
        "    def test_record_event_shape(self):\n"
        '        ev = record_event("signup", {"user": "u1"})\n'
        '        self.assertEqual(ev["kind"], "signup")\n'
        '        self.assertEqual(ev["payload"], {"user": "u1"})\n'
        '        self.assertIn("occurred_at", ev)\n\n'
        "    def test_record_event_emits_utc_timestamp(self):\n"
        '        ev = record_event("signup", {"user": "u1"})\n'
        '        dt = datetime.fromisoformat(ev["occurred_at"])\n'
        "        self.assertIsNotNone(dt.tzinfo)\n"
        "        self.assertEqual(dt.utcoffset(), timedelta(0))\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_no_naive_datetime_guard.py").write_text(
        '"""Structural AST regression guard blocking naive datetime.now() across src/*.py."""\n'
        "import ast\n"
        "import unittest\n"
        "from pathlib import Path\n\n\n"
        "def _find_naive_datetime_now_calls(src_dir: Path) -> list[str]:\n"
        "    violations: list[str] = []\n"
        '    for py_file in sorted(src_dir.rglob("*.py")):\n'
        '        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))\n'
        "        for node in ast.walk(tree):\n"
        "            if not isinstance(node, ast.Call):\n"
        "                continue\n"
        "            func = node.func\n"
        '            if isinstance(func, ast.Attribute) and func.attr == "now":\n'
        "                has_tz_arg = bool(node.args) or any(kw.arg == 'tz' for kw in node.keywords)\n"
        "                if not has_tz_arg:\n"
        '                    violations.append(f"{py_file.name}:{node.lineno}: naive datetime.now() without tz")\n'
        "    return violations\n\n\n"
        "class NaiveDatetimeGuardTest(unittest.TestCase):\n"
        "    def test_no_naive_datetime_now_in_src(self):\n"
        '        src_dir = Path(__file__).resolve().parents[1] / "src"\n'
        "        violations = _find_naive_datetime_now_calls(src_dir)\n"
        '        self.assertEqual(violations, [], "Found naive datetime.now() calls: " + "; ".join(violations))\n',
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Fixed naive `datetime.now()` in `src/events.py` to use `datetime.now(timezone.utc)` and added "
            "a structural AST guard test (`tests/test_no_naive_datetime_guard.py`) that fails whenever any "
            "`src/*.py` module calls `datetime.now()` without an explicit timezone argument. All unit tests pass."
        ),
    }
