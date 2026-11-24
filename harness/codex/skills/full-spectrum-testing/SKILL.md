---
name: full-spectrum-testing
description: "Write a task's tests from its acceptance criteria, across the diamond (a few unit tests, a rich integration layer, chosen end-to-end tests), covering failure modes, edge cases, races, deadlock and livelock, fuzzing and injected faults as well as the happy path. Use when writing a task's tests, or judging whether its tests are enough."
---

# Full-spectrum testing

Write a task's tests from its acceptance criteria, covering every way each can break.

Each test follows the testing Principle (**tests-assert-behaviour**).

1. **Start from the criteria.** List the behaviours each acceptance criterion names. Every test traces to one, and every behaviour has a test. A test that checks no criterion is cut, or a criterion is missing.
2. **Place each test on the diamond.**
   - **Unit:** a piece with real logic of its own, such as a parser, a state machine's transitions or a formula. Few, and chosen.
   - **Integration:** real components together, in process or with real local dependencies, fast enough to run on every change. Most behaviour is proven here.
   - **End to end:** the user's path through the running system, parameterized over the inputs and configurations that matter. Chosen sparingly.
3. **Cover the spectrum**, as it applies to each behaviour:
   - the happy path;
   - failure modes and negative paths: invalid, missing or refused input, errors from dependencies, partial failure;
   - edge cases: empty, one, the maximum, boundaries, unusual encodings;
   - concurrency: races between callers, ordering, and deadlock and livelock wherever locks, retries or waits exist;
   - fuzzing: generated inputs checked against an invariant (property-based);
   - chaos: injected faults, such as a dependency dying, a slow disk, a lost or duplicated message, or a restart mid-operation, and what the user then sees.
4. **Make it deterministic.** Seed generated inputs and fault schedules, control the clock, and force race orderings explicitly (barriers, injected interleavings) rather than hoping the scheduler finds them. A failure prints its seed.
5. **Isolate state.** Each test sets up and tears down its own. Integration and end-to-end scenarios share state only across their own ordered steps.
6. **Red, then green.** Run each new test on the code without the change and watch it fail for the right reason, then make it pass.
7. **Name what each test catches:** the behaviour and the failure, in its name or one line.

Done when every acceptance criterion's behaviours are covered across the spectrum that applies, every new test went red then green, and none depends on timing, load or another test.
