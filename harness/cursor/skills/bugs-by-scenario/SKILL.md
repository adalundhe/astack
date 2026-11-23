---
name: bugs-by-scenario
description: "A failing test or suspected bug is real only when a real scenario shows it: the query, the workload or the benchmark against competitors. Use on a failing test, a list of failures or a suspected bug, before spending time on a fix."
---

# Bugs are proven by scenarios

A failing test or suspected bug is real when a real scenario shows it: the query, the workload, or the benchmark against competitors, run the way a user runs it.

**Why:** lists of failing tests never end, and many entries are about the test, the machine or the clock. The scenario shows what users get.

- Run the scenario. If it misbehaves, write a test that fails for the reason a user sees, then fix the cause.
- If it behaves, write one line and move on.
- Run the failure on main first. If main fails too, it isn't yours: note it, and fix it only if it blocks you.
- A list of failures is never a deliverable.
- "Hard to test" is no excuse. Make the behaviour observable, and write the test that fails on the old code.
