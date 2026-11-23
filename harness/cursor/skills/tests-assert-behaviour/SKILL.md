---
name: tests-assert-behaviour
description: "Tests assert what users of the code can observe, never elapsed time or internals. Use when writing, changing, fixing or keeping a test, and when a timing test flakes."
---

# Tests assert behaviour

A test asserts what the code's users can observe: output, state, errors, work done. Never elapsed time.

**Why:** a timed test measures the machine and its load, not the code.

- No wall-clock assertions. Waiting with a timeout is fine; asserting speed is not.
- When a timing test flakes, remove the clock. Don't widen the bound.
- Prove that work stays bounded by counting rows, allocations, syscalls or requests, and hold the count flat as inputs grow.
- Measure speed in benchmarks (**decide-by-data**, **fair-benchmarks**), not in tests.
- Every fix comes with a test that fails on the old code.
- Test the specified behaviour, not the old implementation.
