"""Separated offline oracle for `skill-bap`."""
from __future__ import annotations

from pathlib import Path

_FIXED_AUDIT = '''from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class AuditEvent:
    actor: str
    action: str
    created_at: datetime


def record_event(actor: str, action: str) -> AuditEvent:
    return AuditEvent(actor=actor, action=action, created_at=datetime.now(timezone.utc))


def format_event_line(event: AuditEvent) -> str:
    if event.created_at.tzinfo is None or event.created_at.utcoffset() != timedelta(0):
        raise ValueError("AuditEvent.created_at must be timezone-aware UTC")
    return f"{event.created_at.isoformat()} {event.actor} {event.action}"
'''

_FIXED_TESTS = '''import ast
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from audit import AuditEvent, format_event_line, record_event


class AuditEventTest(unittest.TestCase):
    def test_record_event_captures_actor_and_action(self):
        ev = record_event("alice", "login")
        self.assertEqual(ev.actor, "alice")
        self.assertEqual(ev.action, "login")

    def test_record_event_uses_utc_aware_timestamp(self):
        ev = record_event("alice", "deploy")
        self.assertIsNotNone(ev.created_at.tzinfo)
        self.assertEqual(ev.created_at.tzinfo, timezone.utc)
        self.assertEqual(ev.created_at.utcoffset(), timedelta(0))
        line = format_event_line(ev)
        self.assertTrue(line.startswith(ev.created_at.isoformat()))
        self.assertIn("+00:00", line)

    def test_format_event_line_rejects_naive_timestamp(self):
        naive = AuditEvent(actor="bob", action="logout", created_at=datetime(2026, 1, 1, 12, 0, 0))
        with self.assertRaises(ValueError):
            format_event_line(naive)

    def test_structural_guard_forbids_naive_datetime_now_in_src(self):
        src_dir = Path(__file__).resolve().parents[1] / "src"
        violations: list[str] = []
        for py_file in sorted(src_dir.rglob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == "utcnow":
                        violations.append(f"{py_file.name}:{node.lineno}: datetime.utcnow()")
                    elif node.func.attr == "now" and not node.args and not node.keywords:
                        violations.append(f"{py_file.name}:{node.lineno}: naive datetime.now()")
        self.assertEqual(violations, [], f"Forbidden naive timestamp call(s): {violations}")


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "audit.py").write_text(_FIXED_AUDIT, encoding="utf-8")
    (repo / "tests" / "test_audit.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Missed rule: `repo/src/` must emit timezone-aware UTC timestamps and never skip regression tests.\n"
            "- **What slipped and why:** `src/audit.py` called naive `datetime.now()` and the UTC regression test in `tests/test_audit.py` was left skipped, removing mechanical enforcement of `program/RULES.md`.\n"
            "- **Fixed (with proof):** Updated `record_event` in `src/audit.py` to `datetime.now(timezone.utc)`, enforced UTC awareness in `format_event_line`, un-skipped `test_record_event_uses_utc_aware_timestamp`, and ran `python3 -B -m unittest discover -s tests` (4 tests OK).\n"
            "- **Guard preventing a repeat:** Added `test_structural_guard_forbids_naive_datetime_now_in_src` in `tests/test_audit.py`, which parses every file under `src/` with `ast` and fails CI if zero-arg `datetime.now()` or `datetime.utcnow()` is introduced."
        ),
    }
