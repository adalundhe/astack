---
name: full-spectrum-testing
description: "Write acceptance-driven tests across the test diamond (unit, integration, end-to-end) covering failure modes, edge cases, concurrency, fuzzing, and injected faults. Use when writing or auditing a task's tests."
---

# Full-spectrum testing

Write tests traced to acceptance criteria that cover the realistic ways behavior can break.

Every test follows **tests-assert-behaviour**.

1. **Map directly to acceptance criteria.** List every user-visible behavior in the criteria; each test traces to one, and every behavior has coverage. Cut tests that check no criterion (or fix missing criteria).
2. **Choose the right layer (test diamond):**
   - **Unit:** focused, pure logic (parsers, state transitions, math). Keep these selective.
   - **Integration:** real components together in-process or against local dependencies, fast enough to run on every change. Prove most behavior here.
   - **End-to-end:** real user flows through the running system across key inputs and configs. Keep these targeted.
3. **Cover every applicable failure class:**
   - **Happy path.**
   - **Failure modes & negative paths:** invalid/missing/rejected input, dependency errors, partial failures.
   - **Edge cases:** empty, single-item, max limits, boundaries, odd encodings.
   - **Concurrency:** races, ordering bugs, deadlocks, and livelocks wherever locks, retries, or waits exist.
   - **Fuzzing / property-based:** seeded generated inputs checked against invariants.
   - **Fault injection / chaos:** dying dependencies, slow disks, lost/duplicated messages, mid-operation restarts, and what users observe.
   - **Rollout & rollback (mixed versions):** when changing DB schemas, auth/IAM/RBAC, infra, or wire/API contracts, run pre-change non-privileged callers/identities and rolled-back versions against post-migration state (**safe-to-deploy**).
4. **Keep tests deterministic.** Seed generated inputs and fault schedules, control clocks, and force interleavings explicitly (barriers or hooks) rather than relying on scheduler luck. Always print the seed on failure.
5. **Isolate state.** Each test creates and cleans up its own state (only sequential steps within one integration/E2E scenario share state).
6. **Verify red, then green.** Run each new test before the fix/feature and confirm it fails for the expected reason before making it pass.
7. **Apply the bad-test brake.** No test is better than a bad test—if a test computes its expected value from the code under test, asserts brittle error prose instead of typed error codes, or stays green when behavior breaks, rewrite or delete it.
8. **Name tests for what they catch:** state the behavior and failure mode in the test name or a one-line description.

Done when every acceptance criterion is covered across applicable layers and failure modes, every new test went red then green, and no test depends on timing, load, or execution order.

Referenced skills: `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`). Read any cited skill file before acting when its trigger applies.
