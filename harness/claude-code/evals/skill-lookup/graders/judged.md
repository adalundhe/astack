---
type: llm
---

Evaluate the pre-planning memory synthesis against `lookup/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` completely clean while verifying saved memories in `program/astack_home/billing/` against live `./repo/src/billing.py`.
- Accurately cites all 3 active sources:
  1. Active lesson `lessons/tax-rounding/LESSON.md` (per-line integer half-up tax rounding `(line_subtotal_cents * tax_rate_bps + 5000) // 10000`, plus related project `ledger-sync` penny parity).
  2. Accepted architecture decision `architecture/AD_1.md` (strict integer minor-unit `*_cents` and `tax_rate_bps`, zero floating-point math).
  3. Contract doc `docs/contracts/api.md` (`POST /v2/invoices`, required `Idempotency-Key` header, `line_items[].unit_price_cents` + `tax_rate_bps`, `201` response fields, default `currency="USD"`).
- Explicitly identifies `lessons/old-vat/LESSON.md` (`legacy_vat_float`) as superseded/retired and excludes it from the plan.

FAIL otherwise.
