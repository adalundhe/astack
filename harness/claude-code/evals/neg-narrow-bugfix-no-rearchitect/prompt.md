---
description: "Negative control: fixing a 1-line off-by-one bug in ./repo/src/window.py stays narrowly scoped and leaves working-but-verbose sibling modules untouched."
expected_outcome: "Fixes only src/window.py (and tests/* if needed), passes all tests, and does not modify src/legacy_export.py or src/reporting.py."
timeout_seconds: 240
---

`/astack:go` Fix the off-by-one bug in `./repo/src/window.py` where `sliding_windows` drops the final window, and verify the test suite in `./repo/tests/` passes.
