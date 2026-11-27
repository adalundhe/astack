"""Separated offline oracle for `rule-minimize-state-stores`."""
from __future__ import annotations

from pathlib import Path

_FIXED_LEDGER = '''from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    account_id: str
    kind: str
    amount_cents: int

    def signed_delta(self) -> int:
        if self.kind == "refund":
            return -self.amount_cents
        return self.amount_cents


class BillingLedger:
    """Single-source-of-truth billing ledger computing derived values on demand."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    def _ensure_unique_id(self, entry_id: str) -> None:
        if any(e.entry_id == entry_id for e in self._entries):
            raise ValueError(f"duplicate entry_id: {entry_id}")

    def record_charge(self, entry_id: str, account_id: str, amount_cents: int) -> LedgerEntry:
        if amount_cents <= 0:
            raise ValueError("charge amount_cents must be > 0")
        self._ensure_unique_id(entry_id)
        entry = LedgerEntry(entry_id, account_id, "charge", amount_cents)
        self._entries.append(entry)
        return entry

    def record_refund(self, entry_id: str, account_id: str, amount_cents: int) -> LedgerEntry:
        if amount_cents <= 0:
            raise ValueError("refund amount_cents must be > 0")
        self._ensure_unique_id(entry_id)
        entry = LedgerEntry(entry_id, account_id, "refund", amount_cents)
        self._entries.append(entry)
        return entry

    def record_adjustment(self, entry_id: str, account_id: str, delta_cents: int) -> LedgerEntry:
        self._ensure_unique_id(entry_id)
        entry = LedgerEntry(entry_id, account_id, "adjustment", delta_cents)
        self._entries.append(entry)
        return entry

    def void_entry(self, entry_id: str) -> None:
        for idx, entry in enumerate(self._entries):
            if entry.entry_id == entry_id:
                del self._entries[idx]
                return
        raise KeyError(entry_id)

    def get_balance(self, account_id: str) -> int:
        return sum(e.signed_delta() for e in self._entries if e.account_id == account_id)

    def account_summary(self, account_id: str) -> dict[str, object]:
        acct_entries = [e for e in self._entries if e.account_id == account_id]
        return {
            "account_id": account_id,
            "balance_cents": sum(e.signed_delta() for e in acct_entries),
            "charge_count": sum(1 for e in acct_entries if e.kind == "charge"),
            "refund_count": sum(1 for e in acct_entries if e.kind == "refund"),
        }

    def all_balances(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for entry in self._entries:
            totals[entry.account_id] = totals.get(entry.account_id, 0) + entry.signed_delta()
        return dict(sorted(totals.items()))
'''

_FIXED_TESTS = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ledger import BillingLedger


class BillingLedgerBaselineTest(unittest.TestCase):
    def test_single_charge_updates_balance(self):
        ledger = BillingLedger()
        ledger.record_charge("e-1", "acct-baseline", 2500)
        self.assertEqual(ledger.get_balance("acct-baseline"), 2500)

    def test_refund_adjustment_and_void_reflect_immediately_after_reads(self):
        ledger = BillingLedger()
        ledger.record_charge("c-1", "acct-1", 4000)
        self.assertEqual(ledger.get_balance("acct-1"), 4000)
        self.assertEqual(ledger.account_summary("acct-1")["charge_count"], 1)

        ledger.record_refund("r-1", "acct-1", 1500)
        self.assertEqual(ledger.get_balance("acct-1"), 2500)
        self.assertEqual(
            ledger.account_summary("acct-1"),
            {"account_id": "acct-1", "balance_cents": 2500, "charge_count": 1, "refund_count": 1},
        )

        ledger.record_adjustment("a-1", "acct-1", -200)
        self.assertEqual(ledger.get_balance("acct-1"), 2300)

        ledger.void_entry("c-1")
        self.assertEqual(ledger.get_balance("acct-1"), -1700)
        self.assertEqual(ledger.account_summary("acct-1")["charge_count"], 0)

    def test_separate_ledger_instances_are_isolated(self):
        first = BillingLedger()
        second = BillingLedger()
        first.record_charge("c-1", "shared-acct", 3000)
        self.assertEqual(second.get_balance("shared-acct"), 0)
        second.record_charge("c-2", "shared-acct", 500)
        self.assertEqual(first.get_balance("shared-acct"), 3000)
        self.assertEqual(second.get_balance("shared-acct"), 500)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "ledger.py").write_text(_FIXED_LEDGER, encoding="utf-8")
    (repo / "tests" / "test_ledger.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Removed _GLOBAL_BALANCE_CACHE, _balance_cache, and _summary_cache from src/ledger.py "
            "so balances and account summaries are computed directly from the ledger entries, and added "
            "tests covering refund/adjustment/void sequences and instance isolation."
        ),
    }
