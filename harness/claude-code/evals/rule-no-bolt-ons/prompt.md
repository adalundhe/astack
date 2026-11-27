---
description: "Fold new customer pricing tiers and volume discounts into a single unified pricing model, removing parallel _v2 copies and boolean mode flags."
expected_outcome: "Reads no-bolt-ons/SKILL.md, removes calculate_price_v2 and use_new_mode/enterprise_override boolean flags from src/pricing.py and src/checkout.py, implements all four tiers and volume breaks with a 40% discount cap in one core model, and adds comprehensive unit tests."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Update the pricing and checkout modules in `./repo` (`src/pricing.py` and `src/checkout.py`) to support the full set of customer tiers (`standard`, `pro`, `enterprise`, `nonprofit`) and volume discounts as one unified model.

Read `./repo/README.md` for the exact pricing rules and public API. Replace the awkward split implementation and mode-switch flags across `src/pricing.py` and `src/checkout.py` with a single first-principles pricing model, update callers, add unit tests under `./repo/tests/` covering every tier, volume break, discount cap, and invalid input, and verify all tests pass.
