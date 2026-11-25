#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Billing Stream Processor

Processes JSON streams of billing events (`charge`, `retry`, `refund`) and sums net cents per account.

## Rules
- `charge`: adds `amount_cents` (`> 0`) to the account's total.
- `retry`: re-attempts a previously failed billing charge with a 10% goodwill discount (`amount_cents * 90 // 100`) when `amount_cents > 0`.
- `refund`: subtracts `amount_cents` (`> 0`) from the account's total.
- Any event with `amount_cents <= 0` is invalid, skipped (adds `0`), and MUST NOT affect any subsequent event.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/processor.py <<'EOF'
from __future__ import annotations

from collections import defaultdict
from typing import Any


class InvoiceProcessor:
    """Processes billing events and accumulates net totals per account."""

    def __init__(self) -> None:
        self._totals: dict[str, int] = defaultdict(int)
        self._in_retry = False
        self._retry_discount_pct = 0
        self.skipped = 0

    def process_event(self, event: dict[str, Any]) -> int:
        account = str(event["account"])
        kind = str(event["kind"])
        amount = int(event["amount_cents"])

        if kind == "retry":
            self._in_retry = True
            self._retry_discount_pct = 10

        if amount <= 0:
            self.skipped += 1
            return 0

        if kind == "refund":
            self._totals[account] -= amount
            return -amount

        applied = amount
        if self._in_retry:
            applied = amount * (100 - self._retry_discount_pct) // 100
            self._in_retry = False
            self._retry_discount_pct = 0

        self._totals[account] += applied
        return applied

    def process_stream(self, events: list[dict[str, Any]]) -> dict[str, int]:
        for event in events:
            self.process_event(event)
        return dict(sorted(self._totals.items()))
EOF

cat > repo/src/cli.py <<'EOF'
#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from processor import InvoiceProcessor  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: cli.py <events.json>", file=sys.stderr)
        return 2
    events = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    proc = InvoiceProcessor()
    totals = proc.process_stream(events)
    print(json.dumps({"totals": totals, "skipped": proc.skipped}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
EOF
chmod +x repo/src/cli.py

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_processor.py <<'EOF'
import sys
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


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial billing stream processor"
git -C repo rev-parse HEAD > program/main_sha.txt

python3 - <<'PY'
import json
from pathlib import Path

events = []
for i in range(1, 121):
    acct = f"acct-{(i % 20) + 1:02d}"
    if i == 74:
        # Invalid retry with 0 amount triggers leaked implicit retry state on the next event
        events.append({"id": i, "account": "acct-05", "kind": "retry", "amount_cents": 0})
    elif i == 75:
        events.append({"id": i, "account": "acct-19", "kind": "charge", "amount_cents": 10000})
    elif i % 15 == 0:
        events.append({"id": i, "account": acct, "kind": "retry", "amount_cents": 2000})
    elif i % 11 == 0:
        events.append({"id": i, "account": acct, "kind": "refund", "amount_cents": 300})
    else:
        events.append({"id": i, "account": acct, "kind": "charge", "amount_cents": 1000})

Path("program/billing_events.json").write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
PY
