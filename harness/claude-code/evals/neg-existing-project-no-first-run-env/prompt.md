---
description: "Negative control: an already-initialized project with existing environment.md does not trigger first-run environment analysis when fixing a simple bug in ./repo/src/calc.py."
expected_outcome: "Fixes discount_price in src/calc.py so tests pass, leaves existing environment.md untouched, and never loads analyze-environment."
timeout_seconds: 180
---

`/astack:go` Fix the discount calculation bug in `./repo/src/calc.py` so `discount_price` subtracts the percentage discount instead of adding it, and ensure `./repo/tests/test_calc.py` passes.
