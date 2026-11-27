---
type: llm
---

Evaluate the contract audit and reduction catalog against `rightsize-contracts/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` completely clean and persists the contract catalog under `program/astack_home/payments-sdk/docs/contracts/` (discoverable via `astack-tools docs list --project payments-sdk --subdir contracts`).
- Grounds findings in exact `src/sdk.py:<line>` citations mapped to real callers (`examples/quickstart.py` and `tests/test_sdk.py`).
- Identifies the concrete surface bloat: duplicate aliases (`amount` vs `amount_cents`, `currency_code` vs `currency`, `cust_id` vs `customer_id`, `timeout_seconds` vs `timeout_ms`), redundant/derivable options (`retry_enabled` redundant with `max_retries=0`; `environment` derivable from `api_key` prefix), dead toggle (`legacy_xml_envelope`), and hidden env var (`PAYMENTS_SDK_FORCE_SYNC_FALLBACK`).
- Orders use cases into clear stepped-complexity tiers with minimal required arguments and sensible defaults, plus safe deprecation/migration guidance.

FAIL otherwise.
