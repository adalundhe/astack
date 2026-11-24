---
name: tests-assert-behaviour
description: "The testing Principle: tests check correctness, meaning behaviour a user can observe, never implementation, machine state or timing; isolated, deterministic, across the full spectrum, diamond-shaped. Use when writing, changing, fixing, reviewing or keeping a test, and when a test flakes."
---

# Tests assert behaviour

A test checks correctness: what the code's users can observe. Never its implementation, the machine's state, or how long it took.

## Start with

1. **Assert behaviour, not implementation:** outputs, state a user can see, errors, and the work done. A refactor that keeps behaviour keeps the tests green.
2. **Assert correctness, not conditions.** Nothing depends on load, core count, scheduling luck or elapsed time. Prove that work stays bounded by counting it (rows, allocations, syscalls, requests) as inputs grow.
3. **Isolate:** each test builds its own state and leaves none behind. Only the ordered steps of one integration or end-to-end scenario share state.
4. **Make it deterministic:** randomness, faults and time come from a seed or a controlled clock, so any failure replays.
5. **Cover the full spectrum:** failure modes, bad input, edge cases, races, deadlock and livelock where concurrency exists, fuzzing and injected faults, as well as the happy path (**full-spectrum-testing**).
6. **Shape it like a diamond:** a few chosen unit tests, a rich and fast integration layer, and thorough but carefully chosen end-to-end tests. Most behaviour is proven in the integration layer.
7. **Red first:** a test for a fix or a feature fails on the code before it.
8. **Measure speed, never assert it:** with **benchmarking**, not in a test.
9. **Treat a flaky test as a bug,** in the test or the code: find which, and never retry it to green.

## Watch for

- assertions on private functions, internal calls, mock call counts or the shape of internal data;
- assertions on timing, speed, core count or load, and sleeps that wait for something to happen;
- tests that share state, depend on order, or fail when run alone or in parallel;
- unseeded randomness, real clocks or a real network deciding the result;
- happy paths only: no failure, edge, race or fault cases;
- retries, quarantines or skips hiding a flaky test;
- tests that already passed on the code before the fix they claim to cover.

**The test:** would this test fail if the behaviour broke, and keep passing if only the implementation changed?

## When it doesn't fit

- counting work (rows, allocations, requests) to prove it stays bounded: that's behaviour;
- waiting with a timeout as a failsafe, without asserting speed;
- mocking an outside system at a production boundary, rather than our own internals;
- pinning the shape of a public interface, which is behaviour to its callers.

**Showing it:** break the code and watch the test stay green; refactor without changing behaviour and watch it fail; run it alone, in parallel, or under load.
