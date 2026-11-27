---
type: llm
---

Evaluate the blast-radius audit against `blast-radius/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` completely clean while auditing `program/proposed_change.patch`.
- Explicitly names and refutes the core safety assumption (that grepping `total_cents(` finds every affected caller).
- Identifies all 3 indirect callers with exact `file:line` citations and concrete failure modes:
  1. `src/invoices.py` (aliased import `compute_order_total`; `running_total += amount` raises `TypeError` adding `dict` to `int`).
  2. `src/exports.py` (two-hop call via `src/pricing.py:quote_amount`; `cents / 100` raises `TypeError` dividing `dict` by `int`).
  3. `src/webhooks.py` (dynamic dispatch via `CALCULATOR_REGISTRY` + `getattr(pricing, fn_name)`; `amount >= high_value_threshold_cents` raises `TypeError`, and outbound webhook JSON `amount_cents` wire contract changes from `int` to `dict`).
- Identifies the cheapest check / safe rollout alternative (e.g. adding a new breakdown function instead of breaking `total_cents`'s return type, and running the downstream consumer test suite).

FAIL otherwise.
