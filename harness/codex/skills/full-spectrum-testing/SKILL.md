---
name: full-spectrum-testing
description: "Write acceptance-driven tests across unit, integration, and E2E layers for failures, edge cases, and faults. Use when writing or auditing a task's tests."
---

# Full-spectrum testing

Write tests traced to acceptance criteria that cover the realistic ways behavior can break.

Every test follows **tests-assert-behaviour**.

1. **Map directly to acceptance criteria.** List every user-visible behavior and trace each test to one. Cut tests checking no criterion, or fix missing criteria.
2. **Choose the right layer (test diamond),** because unit mocks miss real wiring while E2E is too slow for every change:
   - **Unit:** focused, pure logic (parsers, state transitions, math). Keep these selective.
   - **Integration:** real components together in-process or against local dependencies. Run these on every change and prove most behavior here.
   - **End-to-end:** real user flows through the running system across key inputs and configs. Keep these targeted.
3. **Cover every applicable failure class:**
   - **Happy path.**
   - **Failure modes & negative paths:** invalid, missing, or rejected input, dependency errors, and partial failures.
   - **Edge cases:** empty, single-item, max limits, boundaries, and odd encodings.
   - **Concurrency:** races, ordering bugs, deadlocks, and livelocks wherever locks, retries, or waits exist.
   - **Fuzzing / property-based:** seeded generated inputs checked against invariants.
   - **Fault injection / chaos:** dying dependencies, slow disks, lost or duplicated messages, mid-operation restarts, and observed user impact.
   - **Rollout & rollback (mixed versions):** applies to DB schemas, auth/IAM/RBAC, infra, and wire/API contracts (**safe-to-deploy**). Run pre-change non-privileged callers and rolled-back versions against post-migration state.
4. **Keep tests deterministic.** Seed generated inputs and fault schedules, control clocks, and force interleavings with barriers or hooks. Always print the seed on failure.
5. **Isolate state.** Each test creates and cleans up its own state. Only sequential steps inside one integration or E2E scenario share state.
6. **Verify red, then green.** Run each new test before the fix and confirm it fails for the right reason. Never skip red, because a test that never failed may pass tautologically.
7. **Apply the bad-test brake.** No test is better than a bad test. Rewrite or delete any test that derives expected values from the code under test. Also cut tests that check brittle error prose or stay green when behavior breaks.
8. **Name tests for what they catch:** state the behavior and failure mode in the test name or a one-line comment.

**Done when:** every acceptance criterion is covered across applicable layers and failure modes. Every new test went red then green, and no test depends on timing, load, or execution order.

Referenced skills: `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`). Read any cited skill file before acting when its trigger applies.
