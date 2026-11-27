"""Separated offline oracle for `find-it-and-fix-it-bug`."""
from __future__ import annotations

from pathlib import Path

_FIXED_PROCESSOR = '''from __future__ import annotations

from collections import defaultdict
from typing import Any


class InvoiceProcessor:
    """Processes billing events and accumulates net totals per account."""

    def __init__(self) -> None:
        self._totals: dict[str, int] = defaultdict(int)
        self.skipped = 0

    def process_event(self, event: dict[str, Any]) -> int:
        account = str(event["account"])
        kind = str(event["kind"])
        amount = int(event["amount_cents"])

        if amount <= 0:
            self.skipped += 1
            return 0

        if kind == "charge":
            self._totals[account] += amount
            return amount
        if kind == "retry":
            applied = amount * 90 // 100
            self._totals[account] += applied
            return applied
        if kind == "refund":
            self._totals[account] -= amount
            return -amount

        raise ValueError(f"unsupported billing event kind: {kind!r}")

    def process_stream(self, events: list[dict[str, Any]]) -> dict[str, int]:
        for event in events:
            self.process_event(event)
        return dict(sorted(self._totals.items()))
'''

_FIXED_TESTS = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from processor import InvoiceProcessor


class InvoiceProcessorTest(unittest.TestCase):
    def test_charge_and_refund(self):
        proc = InvoiceProcessor()
        totals = proc.process_stream([
            {"account": "acct-1", "kind": "charge", "amount_cents": 2000},
            {"account": "acct-1", "kind": "refund", "amount_cents": 500},
        ])
        self.assertEqual(totals, {"acct-1": 1500})

    def test_valid_retry_applies_goodwill_discount(self):
        proc = InvoiceProcessor()
        totals = proc.process_stream([
            {"account": "acct-2", "kind": "retry", "amount_cents": 1000},
            {"account": "acct-2", "kind": "charge", "amount_cents": 1000},
        ])
        self.assertEqual(totals, {"acct-2": 1900})

    def test_invalid_charge_is_skipped(self):
        proc = InvoiceProcessor()
        totals = proc.process_stream([
            {"account": "acct-3", "kind": "charge", "amount_cents": 0},
            {"account": "acct-3", "kind": "charge", "amount_cents": 1200},
        ])
        self.assertEqual(totals, {"acct-3": 1200})
        self.assertEqual(proc.skipped, 1)

    def test_invalid_retry_does_not_leak_discount_to_next_charge(self):
        proc = InvoiceProcessor()
        totals = proc.process_stream([
            {"account": "acct-05", "kind": "retry", "amount_cents": 0},
            {"account": "acct-19", "kind": "charge", "amount_cents": 10000},
        ])
        self.assertEqual(totals, {"acct-19": 10000})
        self.assertEqual(proc.skipped, 1)

    def test_negative_retry_does_not_affect_subsequent_event(self):
        proc = InvoiceProcessor()
        totals = proc.process_stream([
            {"account": "acct-05", "kind": "retry", "amount_cents": -500},
            {"account": "acct-06", "kind": "charge", "amount_cents": 2500},
        ])
        self.assertEqual(totals, {"acct-06": 2500})
        self.assertEqual(proc.skipped, 1)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "processor.py").write_text(_FIXED_PROCESSOR, encoding="utf-8")
    (repo / "tests" / "test_processor.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Reproduced the wrong invoice total on `program/billing_events.json` (event 74 invalid retry "
            "with `amount_cents=0` leaked `_in_retry=True` onto event 75, discounting `acct-19` from 10000 "
            "to 9000). Removed the implicit `_in_retry` and `_retry_discount_pct` state from "
            "`repo/src/processor.py` so each valid event is computed directly from its own `kind`, added "
            "red-first regression tests in `repo/tests/test_processor.py`, and verified both the test suite "
            "and `repo/src/cli.py program/billing_events.json` match expected totals."
        ),
        "events": [],
    }
