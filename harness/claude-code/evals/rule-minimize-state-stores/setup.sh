#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Billing Ledger

Provides `LedgerEntry` and `BillingLedger` in `src/ledger.py`.

## Rules & Public API
- `LedgerEntry(entry_id: str, account_id: str, kind: str, amount_cents: int)`
  - `kind == "charge"`: adds `amount_cents` (`> 0`) to account balance.
  - `kind == "refund"`: subtracts `amount_cents` (`> 0`) from account balance.
  - `kind == "adjustment"`: adds signed `amount_cents` (`int`) to account balance.
- `BillingLedger()`:
  - Maintains a single source of truth: the ledger entries (`record_*` / `void_entry`).
  - `record_charge(entry_id, account_id, amount_cents) -> LedgerEntry` (raises `ValueError` if `amount_cents <= 0` or duplicate `entry_id`)
  - `record_refund(entry_id, account_id, amount_cents) -> LedgerEntry` (raises `ValueError` if `amount_cents <= 0` or duplicate `entry_id`)
  - `record_adjustment(entry_id, account_id, delta_cents) -> LedgerEntry` (raises `ValueError` if duplicate `entry_id`)
  - `void_entry(entry_id) -> None` (removes entry from ledger; raises `KeyError` if not found)
  - `get_balance(account_id) -> int` (derived directly from current ledger entries; `0` if account has no entries)
  - `account_summary(account_id) -> dict`:
    `{"account_id": account_id, "balance_cents": int, "charge_count": int, "refund_count": int}`
  - `all_balances() -> dict[str, int]` (every account currently present in the ledger mapped to its net balance)
- No unmeasured shadow caches or module-level mutable caches; separate `BillingLedger` instances must be independent.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/ledger.py <<'EOF'
from __future__ import annotations

from dataclasses import dataclass

# Redundant unmeasured global cache shared across BillingLedger instances.
_GLOBAL_BALANCE_CACHE: dict[str, int] = {}


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    account_id: str
    kind: str
    amount_cents: int


class BillingLedger:
    """Billing ledger with unmeasured shadow caches that drift on updates."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []
        self._balance_cache: dict[str, int] = {}
        self._summary_cache: dict[str, dict[str, object]] = {}

    def _ensure_unique_id(self, entry_id: str) -> None:
        if any(e.entry_id == entry_id for e in self._entries):
            raise ValueError(f"duplicate entry_id: {entry_id}")

    def record_charge(self, entry_id: str, account_id: str, amount_cents: int) -> LedgerEntry:
        if amount_cents <= 0:
            raise ValueError("charge amount_cents must be > 0")
        self._ensure_unique_id(entry_id)
        entry = LedgerEntry(entry_id, account_id, "charge", amount_cents)
        self._entries.append(entry)
        new_bal = self._balance_cache.get(account_id, 0) + amount_cents
        self._balance_cache[account_id] = new_bal
        _GLOBAL_BALANCE_CACHE[account_id] = new_bal
        return entry

    def record_refund(self, entry_id: str, account_id: str, amount_cents: int) -> LedgerEntry:
        if amount_cents <= 0:
            raise ValueError("refund amount_cents must be > 0")
        self._ensure_unique_id(entry_id)
        entry = LedgerEntry(entry_id, account_id, "refund", amount_cents)
        self._entries.append(entry)
        # Bug: forgets to update/invalidate _balance_cache, _summary_cache, and _GLOBAL_BALANCE_CACHE
        return entry

    def record_adjustment(self, entry_id: str, account_id: str, delta_cents: int) -> LedgerEntry:
        self._ensure_unique_id(entry_id)
        entry = LedgerEntry(entry_id, account_id, "adjustment", delta_cents)
        self._entries.append(entry)
        # Bug: leaves cached summary and balance stale
        return entry

    def void_entry(self, entry_id: str) -> None:
        for idx, entry in enumerate(self._entries):
            if entry.entry_id == entry_id:
                del self._entries[idx]
                return
        raise KeyError(entry_id)

    def get_balance(self, account_id: str) -> int:
        if account_id in _GLOBAL_BALANCE_CACHE:
            return _GLOBAL_BALANCE_CACHE[account_id]
        if account_id in self._balance_cache:
            return self._balance_cache[account_id]
        total = 0
        for e in self._entries:
            if e.account_id != account_id:
                continue
            if e.kind == "charge" or e.kind == "adjustment":
                total += e.amount_cents
            elif e.kind == "refund":
                total -= e.amount_cents
        self._balance_cache[account_id] = total
        _GLOBAL_BALANCE_CACHE[account_id] = total
        return total

    def account_summary(self, account_id: str) -> dict[str, object]:
        if account_id in self._summary_cache:
            return dict(self._summary_cache[account_id])
        charges = sum(1 for e in self._entries if e.account_id == account_id and e.kind == "charge")
        refunds = sum(1 for e in self._entries if e.account_id == account_id and e.kind == "refund")
        summary: dict[str, object] = {
            "account_id": account_id,
            "balance_cents": self.get_balance(account_id),
            "charge_count": charges,
            "refund_count": refunds,
        }
        self._summary_cache[account_id] = summary
        return dict(summary)

    def all_balances(self) -> dict[str, int]:
        accounts = sorted({e.account_id for e in self._entries})
        return {acct: self.get_balance(acct) for acct in accounts}
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_ledger.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ledger import BillingLedger


class BillingLedgerBaselineTest(unittest.TestCase):
    def test_single_charge_updates_balance(self):
        ledger = BillingLedger()
        ledger.record_charge("e-1", "acct-baseline", 2500)
        self.assertEqual(ledger.get_balance("acct-baseline"), 2500)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial billing ledger scaffold"
