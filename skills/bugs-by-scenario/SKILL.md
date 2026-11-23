---
name: bugs-by-scenario
description: "Decide whether a failing test or suspected bug is real by running the real scenario (the query, the workload, the benchmark against competitors) the way a user would, instead of working through lists of failing tests. Use when you meet a failing test, a list of failures or a suspected bug, and before you spend time fixing one."
---

# Bugs are proven by scenarios

A failing test or a suspected bug counts when a real scenario shows it: the query, the workload, or the benchmark against competitors, run the way a user runs it.

Ada's words: "do NOT get lost in infinite bug fixing. The best way to determine if bugs are real is to actually run or expand the scenarios/queries/cases and run our benchmarks w/ competitors."

**Why:** a list of failing tests never ends, and many entries are about the test, the machine or the clock. The scenario shows what users get.

1. **Run the scenario.** Find the user-facing case the failure would show up in, and run it as a user would. Expand the scenarios when the failure names a case they don't cover yet. **Why:** that is the only run that says whether users are affected.
2. **If the scenario misbehaves, it's a bug.** Write a test that fails for the user-visible reason, then fix the cause. **Why:** a test that fails on the old code and passes on the new is the proof.
3. **If the scenario behaves, write one line** in your report (the test, the scenario you ran, the result) and move on. **Why:** the time goes to the deliverable, not to a test that doesn't stand for a user's problem.
4. **Run it on main before you blame your branch.** If main fails the same way, it's main's. Write one line, and fix it only if it blocks your deliverable. **Why:** a busy main carries its own failures, and chasing them spends your hour on someone else's bug.
5. **Don't open work for a list.** A list of failures is not a deliverable. An entry becomes work when a scenario shows it. **Why:** fixing lists is how a worker's hour ends with its deliverable unbuilt.

Hard to test is no reason to leave a real bug unfixed. Make the behaviour observable (a blocked peer, a counter, a test-only stamp) and write the test that fails on the old code.

You skipped this when you fixed a failing test without running the scenario it stands for, or when an hour went to a list of failures.
