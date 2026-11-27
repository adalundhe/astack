"""Separated offline oracle for `skill-lookup`."""
from __future__ import annotations

from pathlib import Path

CONTEXT_MD = """# Pre-Planning Context Synthesis (`billing`)

## 1. Relevant Repos & Projects
- **`billing` (`./repo/src/billing.py`):** Verified live handler `handle_create_invoice` already enforces `Idempotency-Key`, defaults `currency` to `"USD"`, and computes integer `subtotal_cents`, with `tax_cents: 0` awaiting multi-line tax implementation.
- **`ledger-sync` (related project from `lessons/tax-rounding/LESSON.md`):** Downstream reconciliation checks penny-level parity against `billing` invoice taxes.

## 2. Best Path, Skills & Contract Constraints
- **Active lesson (`lessons/tax-rounding/LESSON.md`):** Compute tax **per line** using integer half-up basis-point rounding `(line_subtotal_cents * tax_rate_bps + 5000) // 10000`, then sum line taxes into `tax_cents`. Include multi-line `.5`-cent tie tests (e.g., `unit_price_cents=100`, `tax_rate_bps=750`, and 3 lines of `333` cents at `825` bps).
- **Accepted Architecture Decision (`architecture/AD_1.md`):** Store and compute all money values strictly as integer minor units (`unit_price_cents`, `subtotal_cents`, `tax_cents`, `total_cents`) and integer `tax_rate_bps`. Zero floating-point arithmetic.
- **Public API Contract (`docs/contracts/api.md`):** `POST /v2/invoices` requires header `Idempotency-Key` (400 if missing), accepts `line_items[{qty, unit_price_cents, tax_rate_bps}]` with optional `currency` defaulting to `"USD"`, and returns `201` with integer `subtotal_cents`, `tax_cents`, and `total_cents = subtotal_cents + tax_cents`.

## 3. Pitfalls to Avoid
- Do not round tax once at the invoice subtotal level (causes 1-cent reconciliation drift in `ledger-sync`).
- Do not use Python's `round()` (banker's half-to-even rounding diverges on `.5` cent ties) or floating-point dollars.
- Do not drop the default `currency="USD"` fallback or the `Idempotency-Key` requirement.

## 4. Stale / Superseded Memory (Ignored)
- **`lessons/old-vat/LESSON.md` (`status: superseded`):** Explicitly ignored. Its retired flat 15% float `legacy_vat_float()` helper was deleted from `repo/src/billing.py` in 2025, violates `AD_1`, and is superseded by `lessons/tax-rounding/LESSON.md`.
"""


def apply(ws: Path) -> dict[str, object]:
    """Write program/CONTEXT.md synthesizing active billing records while ignoring superseded old-vat."""
    (ws / "program" / "CONTEXT.md").write_text(CONTEXT_MD, encoding="utf-8")
    return {
        "final_text": CONTEXT_MD,
    }
