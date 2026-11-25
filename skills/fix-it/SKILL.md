---
name: fix-it
description: "Apply minimal, behavior-proven bug fixes: classify behavior on the desired/expected matrix, prove with failing behavior tests, fix root causes without arbitrary locks, state hacks, or rearchitectures, check broader system and performance impact when relevant, harden tests against lead vectored review, and verify before/after proof. Use whenever fixing a confirmed bug, failure, or regression."
disable-model-invocation: true
---

# Fix it

Fix the confirmed root cause cleanly, minimally, and provably—without adding accidental state, locking hacks, speculative optimizations, or out-of-scope refactors.

## Classify the behavior first

Evaluate both the bug and any side effect your fix introduces along two axes:

- **Desired vs. undesired:** set by the person, documented specs, system goals, and comparable systems (e.g., slow multimedia loads or regular cron errors may be expected, yet undesired).
- **Expected vs. unexpected:** measured empirically from logs, traces, repeated runs, and benchmarks (**find-it**, **benchmarking**).

| | **Expected** | **Unexpected** |
|---|---|---|
| **Desired** | Not a bug. | **Documentation gap:** update README/docs so records match reality (e.g., doubled throughput or halved memory, **technical-writing**). |
| **Undesired** | **Known issue:** check whether remaining failures in the same area or callers mean you patched a symptom instead of the root cause (without expanding scope arbitrarily). | **Novel bug:** if a fix triggers this, shrink the repro (**find-it**) to verify the fix in isolation first, then expand outward (**blast-radius**) to see if callers relied on the old broken behavior—file follow-up issues (**track-it**) or fix within authorized scope. |

## Ten rules for every fix

1. **Repro and behavior test first (**find-it**, **tests-assert-behaviour**):** back every fix with a reproduction and a failing behavior test. Improve or parameterize existing tests covering the scope before adding new ones.
2. **Keep it minimal (**simplify-me**, **yagni**):** write the smallest correct fix using existing patterns, code, architecture, and libraries.
3. **Stay inside the fault boundary (**minimize-state-stores**, **find-it**):** don't add states, duplicate state stores, or refactor outside the affected area identified by **find-it**.
4. **Fix concurrency at the state level (**no-shared-writes**):** treat races, deadlocks, and livelocks as mismanaged state first—never mask them with arbitrary locks, mutexes, or atomic abuse.
5. **Make implicit state machines explicit (**no-implicit-states**):** never hack around a broken state machine; if an implicit state machine caused the bug, make the minimal refactor to turn it into an explicit one.
6. **Let the code speak (**comment-cop**):** don't leave excess comments narrating a fix; clear code and tests explain themselves.
7. **Cover edge cases surfaced by lead review:** the lead's vectored **review** checks edge cases and failure modes intrinsic to the fix; strengthen or parameterize existing tests first and add new tests for every proven gap it finds.
8. **Don't rearchitect inside a bug fix (**rearchitect**):** if the bug comes from a deeper architectural flaw, fix the specific instance cleanly and explain in the PR why the architecture caused it.
9. **Prove before and after (**prove-it**):** a fix is approved only once every identified failure mode reproduces **without** it and disappears **with** it.
10. **Check broader system and performance impact (**benchmarking**, **clamber**, **ab-test**, **never-trade-functionality**):**
    - Assess whether the fix shifts behavior beyond local correctness across key system dimensions: **compute/complexity** (hot paths, parsing, serialization, asymptotic growth), **memory/allocation** (copies, buffer/pool sizing, retention, GC pressure), **storage/queries** (query plans, index usage, N+1s, transaction scope, I/O amplification), **network/protocols** (round trips, fan-out, payload size, framing/multiplexing, handshakes, connection pools, retry/backoff storms), **caching** (hit rates, invalidation scope, TTLs, stampedes), **concurrency/scheduling** (contention, queue depth, backpressure, p99 tail latency), or **startup/resources** (cold starts, bundle/render cost, file descriptors, sockets).
    - When **blast-radius** shows plausible impact on any of these, validate against baseline noise with **benchmarking** to prove no statistically significant regression—without forcing heavy benchmarking on localized fixes with no plausible system impact.
    - Fix performance regressions only with **benchmarking** and **clamber**, never guess or optimize outside scope, and use **ab-test** to prove improvements only when performance is part of the assigned issue.

Finish by running **no-leaked-secrets** on the diff and **cleanup** to remove any `<file>_DEBUG_<shorthash>.<type>` artifacts or temporary instrumentation. In your report to the lead, include every **failed or reverted fix approach and attempt** (what was tried, why it failed or regressed, and the evidence) alongside the final proof so the lead can log `decided:` entries, pass them to post-fix reviewers, and capture durable lessons (**make-it-stick**).
