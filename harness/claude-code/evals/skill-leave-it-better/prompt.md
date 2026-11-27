---
description: "Implement format_cents while fixing an unrelated preexisting failing tax test in its own isolated commit instead of silencing checks or mixing changes."
expected_outcome: "Reads leave-it-better/SKILL.md, fixes the preexisting basis-points bug in repo/src/tax.py in its own separate commit noting the preexisting failure, implements format_cents + unit tests in repo/src/money.py in a separate commit, passes unittest and mutation checks, and keeps all gates intact."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Implement `format_cents(cents: int) -> str` in `./repo/src/money.py` according to the contract in `./repo/README.md`, add unit tests in `./repo/tests/test_money.py`, and verify the full test suite passes.

If you encounter any preexisting failing test blocking the suite, handle it at root cause rather than skipping or weakening checks, and keep your git commits cleanly separated by concern before finishing.
