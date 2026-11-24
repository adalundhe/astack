---
name: benchmarking
description: "Design, run, and write up rigorous benchmarks from performance criteria using user-observable metrics, controlled environments, measured noise, and statistical bars. Use when measuring performance, checking regressions, or comparing systems."
---

# Benchmarking

Write and run benchmarks tied to concrete performance criteria.

Benchmarks follow **tests-assert-behaviour** and **full-spectrum-testing**, except that benchmarks depend on hardware—so keep the machine controlled, recorded, and identical across everything compared.

1. **Start from the criteria.** List each user-observable metric with units: client throughput (req/s), p50/p99/p99.9 latency, process memory, error rate under load. Trace every benchmark to a criterion or an A/B question. Never report a bare ratio like "3x faster" without the two absolute measurements and their spread.
2. **Choose the right layer (test diamond).**
   - **Micro:** one hot function in isolation. Use sparingly to explain bottlenecks, not to decide system-level wins.
   - **Integration:** real components together under a realistic workload. Do most iteration here; it's fast enough to run per change.
   - **End-to-end:** the full system as users run it, parameterized across the claimed scale (1 client to peak, small data to large). Use sparingly as the deciding layer.
3. **Cover the relevant workload spectrum:**
   - **Steady state** under normal load.
   - **Overload:** behavior past capacity (refusals, queueing, errors) and recovery.
   - **Edge cases:** empty, single-item, max size, cold vs. warm cache.
   - **Contention:** peak concurrent clients, lock convoys, fairness.
   - **Fuzzed workloads:** seeded, generated request mixes.
   - **Chaos:** injected faults under load (node crash, slow disk, dropped messages) and user-visible impact.
4. **Control the environment.** Use production builds and settings. Place load generators realistically (e.g., separate machine from server) using whatever machines you can reach; only ask the person for resources only they can provision. Record any environment limitation you can't remove. When comparing against another system, also follow **fair-benchmarks**.
5. **Isolate runs.** Run one benchmark at a time per machine with identical data and warm-up state. Seed every generated workload and fault schedule.
6. **Measure noise and set the bar first.** Run the baseline until each metric's 95% confidence interval for the median is narrower than the smallest meaningful difference (or stops narrowing). Define the acceptance bar before testing changes: a change counts only if it exceeds baseline spread and passes a 95% Mann-Whitney U test or bootstrap interval.
7. **Verify the harness (red, then green).** Run each new benchmark against an intentionally degraded build (injected delay or extra work) to prove it detects regressions. A harness that misses a known regression can't validate an improvement.
8. **Instrument separately and watch for anomalies.** Use counters, profiles, and traces to explain numbers, but run profilers in separate passes so overhead doesn't skew timing. Alternate compared runs round by round, count errors, and verify outputs. Before and after each run, check host load, power source, CPU throttling, memory pressure, disk, and network; discard and rerun anomalous passes.
9. **Explain every number.** Identify the actual bottleneck from profiles and counters, not code guesses. Rule out artifacts (errors, skipped/cached work, dead code, untuned config, noise) with evidence. An unexplained number isn't a valid result.
10. **Label clearly.** State the metric, workload, and criterion each benchmark measures.
11. **Write up the record.** Keep it concise and complete: question, metrics, environment, sampling plan, noise and bar, each result's median/interval/bottleneck, anomalies, conclusion, and exact rerun commands. Save it where the project stores benchmark records.

Done when every performance criterion has benchmarks on the right layer, across applicable workloads, proven to catch regressions, measured against known noise and a pre-set bar, and written up. Only numbers measured this way (or explicitly set by the person) belong in acceptance criteria.

<!-- Adapts pstack's benchmark-checklist and explain-the-number skills and its Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
