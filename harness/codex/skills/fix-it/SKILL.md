---
name: fix-it
description: "Apply minimal, behavior-proven bug fixes: classify behavior on the desired/expected matrix, back with failing behavior tests, fix root causes without state or lock hacks, check plausible system/perf impact, harden tests for review, and prove before/after. Use whenever fixing a confirmed bug."
---

# Fix it

Fix the confirmed root cause cleanly, minimally, and provably. Avoid accidental state, locking hacks, speculative optimizations, and out-of-scope refactors.

## Classify behavior first

Evaluate the bug and any side effect along two axes:

- **Desired vs. undesired:** set by the person, specs, system goals, and comparable systems.
- **Expected vs. unexpected:** measured from logs, traces, repeated runs, and benchmarks (**find-it**, **benchmarking**).

| | **Expected** | **Unexpected** |
|---|---|---|
| **Desired** | Not a bug. | **Doc gap:** update docs to match reality (**technical-writing**). |
| **Undesired** | **Known issue:** check whether remaining failures mean you patched a symptom instead of the root cause. | **Novel bug:** shrink the repro (**find-it**) to test in isolation, check callers (**blast-radius**), and file follow-ups (**track-it**) or fix in scope. |

## Ten rules for every fix

1. **Repro and test first (**find-it**, **tests-assert-behaviour**):** back every fix with a repro and failing behavior test. Strengthen or parameterize existing tests before adding new files.
2. **Keep it minimal (**simplify-me**, **yagni**):** write the smallest correct fix using existing patterns and libraries.
3. **Stay inside the fault boundary (**minimize-state-stores**, **find-it**):** don't add extra states, duplicate stores, or refactor outside the affected area.
4. **Fix concurrency at the state level (**no-shared-writes**):** treat races and deadlocks as mismanaged state first, because arbitrary locks hide bugs instead of solving them.
5. **Make implicit state machines explicit (**no-implicit-states**):** never hack around boolean-flag soup; make the minimal refactor to explicit states.
6. **Let the code speak (**comment-cop**):** clear code and tests explain the fix; skip narrating comments.
7. **Harden against review edge cases:** strengthen tests for every proven edge case or failure mode surfaced by lead **review**.
8. **Don't rearchitect inside a bug fix (**rearchitect**):** fix the specific bug cleanly and note any deeper architectural flaw in the PR.
9. **Prove before and after (**prove-it**):** a fix is done only when every failure reproduces without it and disappears with it.
10. **Check plausible system and perf impact (**benchmarking**, **clamber**, **ab-test**, **never-trade-functionality**):**
    - Check whether the fix plausibly shifts compute complexity, memory/allocations, storage/queries, network/protocols, caching, concurrency/tail latency, or startup/FDs.
    - When **blast-radius** shows plausible impact, benchmark against baseline noise to prove no regression. Skip heavy benchmarking on localized fixes with no plausible system impact.
    - Fix perf regressions only with **benchmarking** and **clamber**; never guess or optimize outside scope.

Finish with **no-leaked-secrets** and **cleanup** (removing `<file>_DEBUG_<shorthash>.<type>` artifacts and temp hooks). Report every **failed or reverted fix approach** to the lead so it gets logged as `decided:`, passed to post-fix reviewers, and preserved via **make-it-stick**.

Referenced skills: `find-it` (`../find-it/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `track-it` (`../track-it/SKILL.md`), `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `simplify-me` (`../simplify-me/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `minimize-state-stores` (`../minimize-state-stores/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `no-implicit-states` (`../no-implicit-states/SKILL.md`), `comment-cop` (`../comment-cop/SKILL.md`), `review` (`../astack-review/SKILL.md`), `rearchitect` (`../rearchitect/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `clamber` (`../clamber/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `never-trade-functionality` (`../never-trade-functionality/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
