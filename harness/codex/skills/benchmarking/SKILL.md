---
name: benchmarking
description: "Design, run, and verify rigorous benchmarks with baseline median and standard deviation (sigma), variance reduction, Amdahl hard-limit checks, proof the work actually ran, and untuned-config checks. Use when measuring performance, checking regressions, or comparing systems."
---

# Benchmarking

Write and run benchmarks tied to concrete performance criteria, grounded in measured variance and physical/algorithmic limits.

Benchmarks follow **tests-assert-behaviour** and **full-spectrum-testing**, except that benchmarks depend on hardware—so keep the machine controlled, recorded, and identical across everything compared.

1. **Start from the criteria.** List each user-observable metric with units: client throughput (req/s), p50/p99/p99.9 latency, process memory, error rate under load. Trace every benchmark to a criterion or an A/B question. Never report a bare ratio like "3x faster" without both absolute measurements and their spread.
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
6. **Measure baseline median, standard deviation ($\sigma$), and variance first.** Run the baseline until each metric's sample standard deviation ($\sigma$), robust spread (IQR/MAD), and 95% CI for the median stabilize. Treat **minimizing measured variance ($\sigma$ and tail spread)** as a first-class objective alongside improving the baseline median. Set the acceptance bar before testing changes, sizing the run count $n$ for the specific regime you are testing:
   - **Location (baseline improvement):** use a 95% Mann-Whitney U test or bootstrap CI on the median/mean difference. Treat $\ge 1\sigma$ as the **step goal / minimum detectable effect** and size $n$ per arm for $\ge 80\%$ power (typically $\sim 16\text{--}20+$ alternating runs per arm)—never require the noisy sample point estimate itself to exceed $1\sigma$, which rejects half of true $1\sigma$ wins.
   - **Broad dispersion reduction ($\sigma$ across runs):** never pair variance cuts with Mann-Whitney U alone (it checks rank-order location and passes equal-median spread cuts only at chance rate, ~5%), and do **not** reuse a location sample size. Pick an explicit target spread ratio (MDE) $r = \sigma_{\text{new}} / \sigma_{\text{base}}$ before running and size $n$ per arm for that target ($n$ scales as $1/(\ln r)^2$: for Brown–Forsythe at $\ge 80\%$ power, halving $\sigma$ [$r = 0.5$] needs $\sim 30\text{--}40$ runs/arm, whereas a 25% cut [$r = 0.75$] needs $\sim 100\text{--}150$ runs/arm). Test with **Brown–Forsythe** and/or a **BCa/studentized 95% bootstrap CI on $\log(\sigma_{\text{new}} / \sigma_{\text{base}}) < 0$** (not an underpowered naive percentile bootstrap), with median non-regressed.
   - **Rare tails and pause spikes:**
     - *Request-level tails (p99/p99.9 pauses inside a workload):* run enough requests **inside each run** to sample the tail reliably (at least $\ge 10/q$ requests per run—e.g. $\ge 1{,}000$ requests for p99), compute each run's own **within-run tail spread ($\text{p99} - \text{p50}$ or $\text{p99.9} - \text{p50}$)**, and compare those per-run tail-spread values across alternating runs with the location test (Mann-Whitney U / 95% bootstrap CI).
     - *Rare whole-run events (e.g. an event hitting 5% of whole runs):* small run counts routinely miss the event completely (at $p = 5\%$, $0.95^{16} = 44\%$ of 16-run baselines see zero events, and Brown–Forsythe down-weights rare outliers by design). Prefer making each run long enough that the event recurs multiple times inside every run (converting it into a within-run tail metric). If whole runs must stay short, you need roughly **$n \ge 7/p$ runs per arm** for ~80% power to detect eliminating a rate-$p$ event completely (e.g. $\sim 140$ runs/arm at $p = 5\%$ via Fisher's exact count test or Brown–Forsythe—and more if the fix only reduces rather than eliminates the rate).
7. **Verify the harness (red, then green).** Run each new benchmark against an intentionally degraded build (injected delay or extra work) to prove it detects regressions. A harness that misses a known regression can't validate an improvement.
8. **Instrument separately and watch for anomalies.** Use counters, profiles, and traces to explain numbers, but run profilers in separate passes so overhead doesn't skew timing. Alternate compared runs round by round, count errors, and verify outputs. Before and after each run, check host load, power source, CPU throttling, memory pressure, disk, and network; discard and rerun anomalous passes.
9. **Check whether the number is real:**
   - **Amdahl / hard-limit check (wall time = CPU + waiting):** verify claimed gains against the fraction $f$ of **end-to-end wall time** actually touched—including both active CPU work **and waiting** (locks/contention, I/O, queueing, scheduling, GC pauses). Removing fraction $f$ of wall time can yield at most $1/(1-f)$ speedup (e.g., cutting 10% of wall time gives at most ~11.1% faster). Measure $f$ from wall-clock / off-CPU + on-CPU profiles, not CPU-only flamegraphs—shortening a lock held across a slow call can legitimately cut wall time far beyond the lock's CPU-only share because it eliminates waiting across threads. If a measured gain exceeds what touched CPU + wait time can explain, stop—it's a broken harness, accidental skip, or measurement artifact.
   - **Prove the work actually ran:** consume/checksum outputs and assert correctness so compilers, JIT dead-code elimination, lazy iterators, or silent errors can't fake speed.
   - **Rule out untuned ceilings:** inspect pool sizes, batch sizes, caches, thread limits, GC, and debug flags on every side—a side held back by a setting is untuned, not slow.
   - **Name the limiter and next $\sigma$-step:** identify the concrete resource or serialization bottleneck from profiles/counters—not guesses—and state what prevents moving another $\ge 1\sigma$ or shrinking $\sigma$ further. An unexplained number isn't a valid result.
10. **Label clearly.** State the metric, workload, and criterion each benchmark measures.
11. **Write up the record.** Keep it concise and complete: question, metrics, environment, sampling plan, baseline median/$\sigma$/bar, each result's median/$\sigma$/interval/limiter, anomalies, conclusion, and exact rerun commands. Save it where the project stores benchmark records.

Done when every performance criterion has benchmarks on the right layer, across applicable workloads, proven to catch regressions, sanity-checked against hard limits and dead work, measured against baseline $\sigma$ and a pre-set bar, and written up. Only numbers measured this way (or explicitly set by the person) belong in acceptance criteria.

Referenced skills: `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `full-spectrum-testing` (`../full-spectrum-testing/SKILL.md`), `fair-benchmarks` (`../fair-benchmarks/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's benchmark-checklist and explain-the-number skills and its Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
