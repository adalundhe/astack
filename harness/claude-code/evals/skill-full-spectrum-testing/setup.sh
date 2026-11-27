#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/ledger.py <<'EOF'
"""Thread-safe atomic account-transfer ledger with JSON file persistence."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path


class AccountLedger:
    """In-memory integer-cent account ledger with atomic transfers and JSON persistence."""

    def __init__(self, initial_balances: dict[str, int] | None = None) -> None:
        self._lock = threading.Lock()
        self._balances: dict[str, int] = {}
        for account, balance in (initial_balances or {}).items():
            if isinstance(balance, bool) or not isinstance(balance, int) or balance < 0:
                raise ValueError(f"invalid initial balance for {account}: {balance}")
            self._balances[account] = balance

    def balance(self, account: str) -> int:
        """Return current integer balance for `account`."""
        with self._lock:
            if account not in self._balances:
                raise KeyError(f"unknown account: {account}")
            return self._balances[account]

    def total_balance(self) -> int:
        """Return sum of all account balances."""
        with self._lock:
            return sum(self._balances.values())

    def snapshot(self) -> dict[str, int]:
        """Return a shallow copy of all account balances."""
        with self._lock:
            return dict(self._balances)

    def transfer(self, src: str, dst: str, amount: int) -> None:
        """Atomically move a positive integer `amount` from `src` to `dst`."""
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("transfer amount must be a positive integer")
        if src == dst:
            raise ValueError("source and destination accounts must differ")
        with self._lock:
            if src not in self._balances or dst not in self._balances:
                raise KeyError("unknown account")
            if self._balances[src] < amount:
                raise ValueError("insufficient funds")
            src_bal = self._balances[src]
            dst_bal = self._balances[dst]
            self._balances[src] = src_bal - amount
            self._balances[dst] = dst_bal + amount

    def save(self, path: Path | str) -> None:
        """Atomically persist balances to a JSON file via temp-file replace."""
        target = Path(path)
        with self._lock:
            payload = json.dumps({"balances": dict(self._balances)}, sort_keys=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)

    @classmethod
    def load(cls, path: Path | str) -> "AccountLedger":
        """Load and validate a ledger snapshot from a JSON file."""
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("balances"), dict):
            raise ValueError("corrupt ledger file")
        return cls(raw["balances"])
EOF

cat > repo/tests/test_ledger.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ledger import AccountLedger


class LedgerTest(unittest.TestCase):
    def test_basic_transfer(self):
        ledger = AccountLedger({"alice": 100, "bob": 50})
        ledger.transfer("alice", "bob", 40)
        self.assertEqual(ledger.balance("alice"), 60)
        self.assertEqual(ledger.balance("bob"), 90)
EOF

cat > program/testing_brief.md <<'EOF'
# Test Coverage Expansion: `AccountLedger`

`./repo/src/ledger.py` implements an atomic account-transfer ledger, but `./repo/tests/test_ledger.py` currently has only a single trivial happy-path test.

Acceptance criteria to test under `./repo/tests/` (do not modify `./repo/src/ledger.py`):
1. **Negative paths:** reject negative, zero, and boolean transfer amounts; reject insufficient funds without mutating balances; reject same-account and unknown-account transfers; reject negative initial balances.
2. **Boundary and edge cases:** drain exact remaining balance to zero, transfer 1 cent, empty ledger total == 0, isolated state per test.
3. **Concurrency:** launch multiple threads synchronized with `threading.Barrier` performing concurrent transfers on shared accounts and verify exact total balance conservation and expected final balances.
4. **Seeded property / fuzzing:** generate a deterministic seeded sequence of randomized transfers (`random.Random(seed)`) and verify total-balance conservation and non-negative balances after every step, printing the seed in failure messages.
5. **Persistence and fault checks:** round-trip `save` and `load` in an isolated temporary directory confirming exact balances restored with no leftover `.tmp` file, and reject malformed/corrupt JSON files.
EOF

git -C repo add .
git -C repo commit -q -m "initial account ledger with single happy-path test"
