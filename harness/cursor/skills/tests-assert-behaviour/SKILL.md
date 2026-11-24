---
name: tests-assert-behaviour
description: "Keep tests asserting user-observable behavior—not internals, machine state, or timing—isolated, deterministic, red-first, and diamond-shaped. Use when writing, reviewing, or fixing flaky tests."
disable-model-invocation: true
---

# Tests assert behaviour

Tests verify user-observable correctness—never internal implementation details, machine state, or wall-clock timing.

## Start with

1. **Assert observable behavior:** outputs, visible state, errors, and bounded work. Behavior-preserving refactors should keep tests green.
2. **Stay independent of hardware and load.** Never depend on core count, scheduling luck, or elapsed wall time. Verify complexity bounds by counting work (rows, allocations, syscalls, requests) as input scales.
3. **Isolate state:** every test sets up and tears down its own state (only ordered steps within a single integration or E2E scenario share state).
4. **Stay deterministic:** drive randomness, faults, and time from explicit seeds or controlled clocks so every failure replays cleanly.
5. **Test beyond the happy path:** cover failure modes, bad inputs, edge cases, concurrency/races/deadlocks, fuzzing, and injected faults (**full-spectrum-testing**).
6. **Use a test diamond:** selective unit tests, a fast comprehensive integration layer (where most behavior is proven), and targeted end-to-end tests.
7. **Go red first:** confirm new tests fail before the fix or feature lands.
8. **Benchmark speed separately:** measure performance via **benchmarking**, never assert latency inside unit/integration tests.
9. **Fix flakes at the root:** a flaky test is a bug in the test or product code—find which and fix it instead of retrying to green.

## Watch for

- assertions on private functions, internal call sequences, mock invocation counts, or internal struct shapes;
- assertions on elapsed time, speed, or host load, and `sleep` calls waiting for async state;
- tests sharing state, depending on run order, or failing alone or under parallelism;
- unseeded randomness, real wall clocks, or live external networks deciding pass/fail;
- happy-path-only coverage with no failure, edge, concurrency, or fault tests;
- retry wrappers, skips, or quarantines masking flakes;
- tests that already passed before the bug fix they claim to verify.

**The test:** would this fail if user-visible behavior broke, and keep passing if only internal implementation changed?

## When it doesn't fit

- counting work (rows, allocations, queries) to prove algorithmic bounds—that's observable behavior;
- generous safety timeouts that prevent infinite hangs without asserting performance;
- mocking external third-party systems at a production boundary (not internal modules);
- pinning a public library/API contract, which *is* behavior to its callers.

**Showing it:** break the behavior and watch the test stay green; refactor internals without changing behavior and watch it fail; run the test solo, in parallel, or under load.
