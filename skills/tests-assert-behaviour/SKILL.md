---
name: tests-assert-behaviour
description: "Write tests that assert what users of the code can observe, never elapsed time or internals. Use when you write, change, fix or keep a test, and when a timing test flakes."
---

# Tests assert behaviour

A test asserts what the code's users can observe: outputs, state, errors, the work done. Never elapsed time.

Ada's words: "Are we testing behavior or implementation?"

**Why:** a test that times code measures the machine and its load against a picked number. It passes on a fast, quiet machine and fails on a busy one with the code unchanged.

- **No wall-clock assertions.** A timeout while waiting for something to happen is fine; it isn't a claim about speed. **Why:** speed in a test is a property of the machine that runs it.
- **When a timing test flakes, take the clock out.** Don't loosen its bound or change its statistic. Keep or add what it says about behaviour. **Why:** a looser bound flakes later, and still says nothing about behaviour.
- **Prove bounded work by counting**: rows read, allocations, syscalls, wakeups, requests made, re-renders of something unchanged. Hold the count flat across input sizes rather than under a picked threshold. **Why:** counts don't depend on the machine, and a flat count is the real claim.
- **Measure speed, don't assert it**, in a benchmark reported as a measurement (**decide-by-data**, **fair-benchmarks**). **Why:** a speed claim needs noise, load and a comparison, which a unit test can't hold.
- **A fix comes with a test that fails on the old code** and passes on the new. **Why:** a test that passes both ways proves nothing.
- **Test the specified behaviour, not the old code.** Old code can serve as an oracle while you work. Delete it before you hand over. **Why:** a test pinned to the old implementation fails every correct change.

You skipped this when a test compares a duration to a number, or when a flaky test was made to pass by widening its bound.
