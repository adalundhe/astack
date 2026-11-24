#!/bin/bash
set -euo pipefail
mkdir -p program repo
if [ -n "${ASTACK_EVAL_SETTINGS_JSON:-}" ]; then
  printf '%s\n' "$ASTACK_EVAL_SETTINGS_JSON" > program/settings.json
else
cat > program/settings.json <<'EOF'
{
  "roles": {
    "worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  },
  "reviewer_pool": [
    {"provider": "anthropic", "model": "opus", "effort": "medium"},
    {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
    {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  ]
}
EOF
fi

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false
cat > repo/ledger_store.py <<'EOF'
from __future__ import annotations

import threading
from pathlib import Path


class LedgerStore:
    def __init__(self, initial: dict[str, int] | None = None):
        self._lock = threading.Lock()
        self._balances: dict[str, int] = dict(initial or {})

    def balance(self, account: str) -> int:
        with self._lock:
            return self._balances.get(account, 0)

    def transfer(self, src: str, dst: str, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        with self._lock:
            if self._balances.get(src, 0) < amount:
                raise ValueError("insufficient funds")
            self._balances[src] = self._balances.get(src, 0) - amount
            self._balances[dst] = self._balances.get(dst, 0) + amount
EOF
git -C repo add ledger_store.py
git -C repo commit -q -m "initial thread-safe single-transfer ledger store"

# Branch introduces 3 planted blocking bugs of varying difficulty + 1 minor nit:
#   1. Easy (blocking): transfer_batch accepts negative amounts (drains dst into src).
#   2. Medium (blocking): transfer_batch checks balances under one lock, releases lock, then mutates under a second lock (concurrent double-spend race).
#   3. Hard (blocking): load_snapshot drops the final account record whenever the file has no trailing newline (`text.split("\n")[:-1]`), while save_snapshot writes `"\n".join(...)` with NO trailing newline — silently wiping the last account on every round-trip!
#   4. Minor (non-blocking nit): redundant narrating comment `# update total`.
git -C repo checkout -q -b lane/batch-transfer
cat > repo/ledger_store.py <<'EOF'
from __future__ import annotations

import threading
from pathlib import Path


class LedgerStore:
    def __init__(self, initial: dict[str, int] | None = None):
        self._lock = threading.Lock()
        self._balances: dict[str, int] = dict(initial or {})
        self.transfers_applied = 0

    def balance(self, account: str) -> int:
        with self._lock:
            return self._balances.get(account, 0)

    def transfer(self, src: str, dst: str, amount: int) -> None:
        if amount <= 0:
            raise ValueError("amount must be positive")
        with self._lock:
            if self._balances.get(src, 0) < amount:
                raise ValueError("insufficient funds")
            self._balances[src] = self._balances.get(src, 0) - amount
            self._balances[dst] = self._balances.get(dst, 0) + amount
            # update total
            self.transfers_applied += 1

    def transfer_batch(self, items: list[tuple[str, str, int]]) -> None:
        with self._lock:
            staged = dict(self._balances)
            for src, dst, amount in items:
                if staged.get(src, 0) < amount:
                    raise ValueError("insufficient funds")
                staged[src] = staged.get(src, 0) - amount
                staged[dst] = staged.get(dst, 0) + amount
        with self._lock:
            for src, dst, amount in items:
                self._balances[src] = self._balances.get(src, 0) - amount
                self._balances[dst] = self._balances.get(dst, 0) + amount
                self.transfers_applied += 1

    def save_snapshot(self, path: Path) -> None:
        with self._lock:
            rows = [f"{acct}:{bal}" for acct, bal in sorted(self._balances.items())]
        Path(path).write_text("\n".join(rows), encoding="utf-8")

    def load_snapshot(self, path: Path) -> None:
        text = Path(path).read_text(encoding="utf-8")
        restored: dict[str, int] = {}
        for line in text.split("\n")[:-1]:
            if not line:
                continue
            acct, raw_bal = line.split(":", 1)
            restored[acct] = int(raw_bal)
        with self._lock:
            self._balances = restored
EOF
git -C repo add ledger_store.py
git -C repo commit -q -m "add batch transfers and snapshot persistence"
git -C repo diff main..lane/batch-transfer > program/change.diff
mkdir -p program/base
git -C repo show main:ledger_store.py > program/base/ledger_store.py
