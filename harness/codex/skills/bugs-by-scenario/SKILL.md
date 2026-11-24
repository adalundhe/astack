---
name: bugs-by-scenario
description: "Confirm a failing test or suspected bug with a realistic user scenario (and check whether main already fails) before fixing it. Use on failing tests, failure lists, or suspected bugs."
---

# Bugs by scenario

Confirm a bug with a real user scenario (workflow, query, workload, or benchmark run the way a user runs it) before spending time fixing it.

- Run the real scenario. If it misbehaves, write a failing test that captures what the user sees, then fix the root cause.
- If the real scenario works fine, log a one-line note and move on.
- Test the failure on `main` first. If `main` already fails, it isn't caused by your change: note it, and fix it only if it blocks your work.
- A list of failing tests is never a deliverable.
- "Hard to test" isn't an excuse—make the behavior observable and write a test that fails before the fix.
