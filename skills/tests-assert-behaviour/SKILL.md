---
name: tests-assert-behaviour
description: "Assert observable behavior with independent oracles, typed errors, and deterministic red-first tests. Use when writing, reviewing, or fixing tests."
disable-model-invocation: true
---

# Tests assert behaviour

Tests verify objective behavior of functions and systems. Never assert internal details, architectural judgment, machine timing, or tautologies.

**No test is better than a bad test.** A test that passes when behavior breaks—or blocks valid design choices—wastes time and gives false confidence. Rewrite or delete it instead of keeping it for coverage.

## Start with

1. **Assert observable behavior, never judgment:** verify outputs, visible state, errors, and bounded work. Behavior-preserving refactors and valid design choices must stay green.
2. **Use an independent oracle:** never compute expected values with the code under test. Never assert on stub or mock data the test built without running real production logic. Both are tautologies that prove nothing. Use hand-worked constants, an independent reference, round-trip invariants, or verified fixtures.
3. **Assert typed errors, not prose:** check the exception class, error code, exit status, or HTTP status callers branch on. Avoid matching English wording unless the exact message is a documented user contract.
4. **Stay independent of hardware and load:** never rely on core count, scheduling luck, or elapsed wall time. Prove complexity bounds by counting work (rows, allocations, syscalls, queries) as input scales.
5. **Isolate state:** every test creates and tears down its own state. Only ordered steps inside one integration or E2E scenario share state.
6. **Stay deterministic:** drive randomness, faults, and clocks from explicit seeds or fake clocks so every failure replays cleanly.
7. **Test beyond the happy path:** cover failure modes, bad inputs, edge cases, concurrency, fuzzing, and injected faults (**full-spectrum-testing**).
8. **Use a test diamond:** keep unit tests selective, prove most behavior in fast integration tests, and add targeted end-to-end tests.
9. **Go red first:** confirm new tests fail before the fix lands, because a test that already passes proves nothing about the change.
10. **Benchmark speed separately:** measure latency via **benchmarking**, never inside unit or integration tests.
11. **Fix flakes at the root:** a flaky test signals a real bug in the test or product code, because retries only hide intermittent failures. Diagnose which (**find-it**) and fix the cause.

## Watch for

- `assertEqual(got, prodHelper(x))` — tautological expected values;
- `assert mock_repo.get() == fixture` — testing self-built stubs;
- `assert "timeout" in str(err)` — brittle error prose;
- `assert mock.call_count == 2` — private call-order assertions;
- `assert "PatternX" not in config` — arbitrary tests policing design judgment;
- `assert elapsed_ms < 50` or `sleep(0.5)` — timing-dependent assertions;
- `pytest.mark.flaky(reruns=3)` or `@skip` — masked flakes;
- shared mutable globals or order-dependent test suites;
- unseeded `random()`, live `time.now()`, or real external URLs;
- happy-path-only tests with zero error or boundary cases;
- regression tests that pass before the fix is applied.

**The test:** would this fail if user-visible behavior broke, and stay green if only internals changed?

## When it doesn't fit

- counting work (rows, allocations, queries) to prove algorithmic bounds;
- generous safety timeouts that stop infinite hangs without asserting speed;
- mocking third-party systems at an external boundary (never internal modules);
- pinning a documented public API or user-facing error format.

**Showing it:** break the behavior and watch the test stay green; refactor internals without changing behavior and watch it fail; run the test solo, in parallel, and under load.

<!-- Adapts pstack's testing principles and TDD guardrails (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
