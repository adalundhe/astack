---
type: llm
---

Evaluate the changes in `./repo` and the final summary against `no-bolt-ons`.

PASS if all of these hold:
- Removes `calculate_price_v2` and mode-switch boolean flags (`use_new_mode`, `enterprise_override`) from both `src/pricing.py` and `src/checkout.py`.
- Folds all four customer tiers (`standard`, `pro`, `enterprise`, `nonprofit`), volume discounts, the 40% discount cap, and input validation into a single core pricing model.
- Updates callers (`checkout.quote_order`) and adds unit tests covering all tiers, volume breaks, the cap, and invalid inputs.

FAIL otherwise.
