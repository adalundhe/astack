---
description: "Fixes discount/tax pricing bugs missed by a slow mock-coupled test suite and replaces internal mock-call and sleep assertions with fast behavior tests using independent oracles."
expected_outcome: "Reads tests-assert-behaviour/SKILL.md, fixes post-discount tax calculation and FLAT500 zero-floor in repo/src/checkout.py, removes MagicMock/patch internal helper assertions and time.sleep(0.5) from repo/tests/test_checkout.py, and writes deterministic behavior tests that catch regressions."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Customers report incorrect checkout totals from `./repo/src/checkout.py` (see `./repo/README.md` for the exact pricing specification), even though `./repo/tests/test_checkout.py` currently passes and takes over half a second to run.

Fix the checkout pricing defects in `./repo/src/checkout.py`, and rewrite `./repo/tests/test_checkout.py` so the test suite verifies the observable pricing contract directly across normal, boundary, and invalid inputs without coupling to internal helpers or wall-clock sleeps.
