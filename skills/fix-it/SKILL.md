---
name: fix-it
description: "Apply minimal, behavior-proven fixes to confirmed root causes without state hacks or regressions. Use whenever fixing a confirmed bug."
disable-model-invocation: true
---

# Fix it

Fix the confirmed root cause cleanly, minimally, and provably. Avoid accidental state, lock hacks, speculative optimizations, and out-of-scope refactors.

**Role guard:** workers and single-agent hosts only—read-only reviewers diagnose and verify, never apply fixes.

## Classify behavior first

Evaluate the bug and any side effect along two axes:

- **Desired vs. undesired:** set by the person, specs, system goals, and comparable systems.
- **Expected vs. unexpected:** measured from logs, traces, repeated runs, and benchmarks (**find-it**, **benchmarking**).

| | **Expected** | **Unexpected** |
|---|---|---|
| **Desired** | Not a bug. | **Doc gap:** update docs to match reality. |
| **Undesired** | **Known issue:** check whether remaining failures mean you patched a symptom instead of the root cause. | **Novel bug:** shrink the repro (**find-it**), check callers (**blast-radius**), and fix in scope or log a follow-up. |

## Ten rules for every fix

1. **Repro and test first (**find-it**):** back every fix with a repro and failing behavior test. Extend existing tests before adding files.
2. **Keep it minimal:** write the smallest correct fix using existing patterns, because broad edits widen blast radius and mask regressions.
3. **Stay inside the fault boundary:** avoid extra state, duplicate stores, or unrelated refactors, because extra state drifts and creates new bugs.
4. **Fix concurrency at the state level:** treat races and deadlocks as mismanaged state first, because arbitrary locks hide bugs instead of solving them.
5. **Make implicit state machines explicit:** replace boolean-flag soup with explicit states, because flag combinations hide impossible transitions.
6. **Let the code speak:** clear code and tests explain the fix; skip narrating comments.
7. **Harden against review edge cases:** strengthen tests for every proven edge case or failure mode surfaced in review.
8. **Don't rearchitect inside a bug fix:** fix the specific bug cleanly and note deeper flaws in the PR, because mixed refactors obscure root-cause verification.
9. **Prove before and after (**prove-it**):** a fix is done only when every failure reproduces without it and disappears with it.
10. **Check plausible system and perf impact:**
    - Check shifts in compute, memory, storage, network, caching, tail latency, or FDs.
    - When **blast-radius** shows plausible impact, benchmark against baseline noise via **benchmarking**. Skip heavy benchmarking on localized fixes.
    - Fix perf regressions only with measured profiles; never guess or optimize outside scope.

Finish with **cleanup** to delete `<file>_DEBUG_<shorthash>.<type>` files, temp hooks, and any secrets. Report every **failed or reverted fix approach** to the lead for `decided:` and review.

**Done when:** the failing test goes red-to-green, plausible impact is checked, artifacts are cleaned, and failed approaches are reported.
