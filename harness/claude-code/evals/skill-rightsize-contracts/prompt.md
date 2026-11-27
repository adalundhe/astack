---
description: "Atomic outcome eval for rightsize-contracts: audits the bloated 14-parameter public contract and hidden env toggle in repo/src/sdk.py, publishes a stepped-complexity reduction catalog under ASTACK_HOME/payments-sdk/docs/contracts/ verified by astack-tools docs list, and keeps ./repo clean."
expected_outcome: "Reads rightsize-contracts/SKILL.md, audits repo/src/sdk.py alongside tests and quickstart usage without editing ./repo, publishes a reduction catalog under program/astack_home/payments-sdk/docs/contracts/ naming exact src/sdk.py:line definitions, duplicate aliases/redundant parameters to collapse, the undocumented PAYMENTS_SDK_FORCE_SYNC_FALLBACK toggle, stepped-complexity tiers with defaults, and safe migration steps."
timeout_seconds: 360
---

`/astack:go` The public charge API in `./repo/src/sdk.py` for project `payments-sdk` has accumulated redundant parameters, duplicate aliases, and undocumented toggles. Using `program/astack_home` as `ASTACK_HOME`, audit the contract surface against `./repo/examples/quickstart.py` and `./repo/tests/test_sdk.py` without modifying `./repo`, and publish a concrete contract catalog and reduction plan under the project's `docs/contracts/` store outside the repo.
