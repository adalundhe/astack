"""Separated offline oracle for `skill-run-it-back`."""
from __future__ import annotations

from pathlib import Path

_ALIGNMENT = """# Alignment Restatement

1. **Goal:** Give finance ops a single command to export active invoices (`status == "active"`) as a CSV (`invoice_id,customer,amount_cents,status`) ready for Friday reconciliation.
2. **Problem:** Finance analysts currently copy invoice rows by hand into spreadsheets, accidentally including `void` and `archived` invoices and delaying weekly close by half a day.
3. **In-scope deliverable:** Add an active-invoice CSV export helper/CLI in `./repo/src/invoices.py` plus unit tests in `./repo/tests/test_invoices.py` covering filtering (`status == "active"` only) and CSV formatting.
4. **Done when:** Running `python3 -B -m unittest discover -s tests` exits 0 and running the CSV export command against `list_invoices()` emits header `invoice_id,customer,amount_cents,status` followed exclusively by active rows (`INV-1001`, `INV-1003`), excluding `void` (`INV-1002`) and `archived` (`INV-1004`) rows.
5. **Out of scope:**
   - **No PDF export** or branded PDF rendering (blocked on legal template approval).
   - **No DB migration** or schema alteration (DBA freeze active through end of quarter).
   - Adjacent note only: billing portal dark-mode styling is separate and will not be touched.
6. **Assumptions:**
   - `amount_cents` stays an integer column in cents (no currency formatting or rounding conversion).
   - Standard RFC 4180 UTF-8 CSV with header row `invoice_id,customer,amount_cents,status` is accepted by finance's workbook.
   - `./repo` remains untouched until you confirm or strike any line above.
"""


def apply(ws: Path) -> dict[str, object]:
    out = ws / "program" / "ALIGNMENT.md"
    out.write_text(_ALIGNMENT, encoding="utf-8")
    return {"final_text": _ALIGNMENT}
