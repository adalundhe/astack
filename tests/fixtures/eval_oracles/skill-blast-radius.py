"""Separated offline oracle for `skill-blast-radius`."""
from __future__ import annotations

from pathlib import Path

REPORT = """# Blast Radius Audit: `src/pricing.py:total_cents` Return-Type Change

## What Changed & Core Safety Assumption
- **Proposed diff:** `src/pricing.py:5-9` changes `total_cents(items, tax_bps)` from returning `int` to returning `dict[str, int]` (`{"subtotal_cents", "tax_cents", "total_cents"}`).
- **Core safety assumption (DISPROVEN / FALSE):** The author assumes grepping for `total_cents(` surfaces every impacted caller. In reality, three indirect consumers bypass a literal `total_cents(` search via aliased import, a delegating wrapper, and dynamic string registry dispatch—all three crash at runtime and one alters an external wire schema.

## Concrete Risks & Indirect Callers

1. **Aliased import in invoice batching — `src/invoices.py:4`, `src/invoices.py:13-14`** (Severity: High, Likelihood: Certain)
   - `src/invoices.py:4` aliases `from src.pricing import total_cents as compute_order_total`.
   - `src/invoices.py:13-14` computes `amount = compute_order_total(items, tax_bps)` and executes `running_total += amount`.
   - **Failure mode:** Raises `TypeError: unsupported operand type(s) for +=: 'int' and 'dict'` on the first order in every batch.

2. **Two-hop wrapper consumer in CSV export — `src/pricing.py:12-14`, `src/exports.py:4`, `src/exports.py:9-10`** (Severity: High, Likelihood: Certain)
   - `src/exports.py:9` calls `quote_amount(items, tax_bps)` (which delegates directly to `total_cents` in `src/pricing.py:14`).
   - `src/exports.py:10` formats `f"{cents / 100:.2f}"`.
   - **Failure mode:** Raises `TypeError: unsupported operand type(s) for /: 'dict' and 'int'`, breaking finance reconciliation CSV exports.

3. **Dynamic registry dispatch & outbound wire schema in webhooks — `src/webhooks.py:6-8`, `src/webhooks.py:18-24`** (Severity: Critical, Likelihood: Certain)
   - `src/webhooks.py:6-8` maps `"invoice.created"` to the string `"total_cents"` in `CALCULATOR_REGISTRY`, and `src/webhooks.py:18-20` invokes `getattr(pricing, fn_name)(items, tax_bps)` dynamically.
   - **Failure mode 1 (Runtime crash):** `src/webhooks.py:24` evaluates `amount >= high_value_threshold_cents`, raising `TypeError: '>=' not supported between instances of 'dict' and 'int'`.
   - **Failure mode 2 (External wire contract break):** `src/webhooks.py:23` emits `"amount_cents": amount`, turning an integer JSON field into a nested object for downstream webhook receivers even if the comparison were fixed.

## What Held & Cheapest Check
- **Held:** Only the pure subtotal/tax arithmetic inside `src/pricing.py` itself stays internally valid.
- **Cheapest check:** Running `python3 -m unittest discover -s tests` (`tests/test_pricing.py`) immediately exercises all three indirect callers and catches every `TypeError` before merge.
- **Safer rollout:** Keep `total_cents(...) -> int` unchanged and introduce a new additive function `price_breakdown(...) -> dict[str, int]` (expand -> switch -> contract).
"""


def apply(ws: Path) -> dict[str, object]:
    """Write program/BLAST_RADIUS.md naming all 3 indirect callers with exact file:line citations, leaving ./repo clean."""
    (ws / "program" / "BLAST_RADIUS.md").write_text(REPORT, encoding="utf-8")
    return {
        "final_text": (
            "Wrote blast-radius audit to `program/BLAST_RADIUS.md` without modifying `./repo`. "
            "The author's grep-based safety assumption is false: changing `total_cents` to return `dict` breaks "
            "`src/invoices.py:14` (`compute_order_total` alias, `TypeError` on `+=`), "
            "`src/exports.py:10` (two-hop `quote_amount`, `TypeError` on `/ 100`), and "
            "`src/webhooks.py:19-24` (dynamic `CALCULATOR_REGISTRY` + `getattr`, `TypeError` on `>=` plus JSON `amount_cents` schema break)."
        ),
    }
