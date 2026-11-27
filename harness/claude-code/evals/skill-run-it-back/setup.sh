#!/usr/bin/env bash
set -euo pipefail

mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/invoices.py <<'EOF'
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer: str
    amount_cents: int
    status: str  # "active" | "void" | "archived"


def list_invoices() -> list[Invoice]:
    return [
        Invoice(invoice_id="INV-1001", customer="Acme Corp", amount_cents=125000, status="active"),
        Invoice(invoice_id="INV-1002", customer="Globex LLC", amount_cents=48000, status="void"),
        Invoice(invoice_id="INV-1003", customer="Initech", amount_cents=91000, status="active"),
        Invoice(invoice_id="INV-1004", customer="Umbrella", amount_cents=33000, status="archived"),
    ]
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_invoices.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from invoices import list_invoices


class InvoicesTest(unittest.TestCase):
    def test_list_invoices_returns_all_statuses(self):
        statuses = {inv.status for inv in list_invoices()}
        self.assertEqual(statuses, {"active", "void", "archived"})


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial invoices module and baseline test"

cat > program/ask.md <<'EOF'
# Stakeholder Message — Finance Ops Friday Reconciliation

Hey team, quick brain dump from our Friday close sync. Right now the finance analysts are manually copying active invoices out of the app into spreadsheets every week, and people keep accidentally including voided or archived invoices which breaks reconciliation and delays close by half a day.

What we actually need in this pass is a straightforward CSV export of **active** invoices (`status == "active"`) with columns `invoice_id,customer,amount_cents,status` so finance can run one export command and drop the file straight into their reconciliation workbook.

Just to be super clear about what we are NOT doing yet (folks kept bringing these up in Slack):
- Do **not** build PDF invoice export or PDF rendering right now — legal has not signed off on the branded PDF template yet.
- Do **not** run any database schema migration or alter existing invoice storage schemas right now — DBA freeze is active through end of quarter.

Also someone mentioned dark-mode styling on the billing portal; that's completely unrelated to this request so just note it separately if needed.
EOF
