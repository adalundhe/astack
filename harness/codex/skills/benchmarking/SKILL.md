---
name: benchmarking
description: "Design, run, and verify rigorous benchmarks with baseline variance, Amdahl checks, and real-work proof. Use when measuring performance or comparing systems."
---

# Benchmarking

Tie every benchmark to concrete performance criteria, measured variance, and physical limits. Follow **tests-assert-behaviour**, and keep hardware controlled, recorded, and identical across comparisons.

1. **Start from the criteria:** list each user-observable metric with units (req/s, p50/p99/p99.9 latency, RSS, error rate). Never report a bare ratio like "3x faster", because ratios without absolute numbers and spread hide tiny baselines and noisy variance.
2. **Choose the right layer:**
   - **Micro:** one hot function alone. Use to explain bottlenecks, not to declare system wins.
   - **Integration:** real components under realistic load. Iterate here per change.
   - **End-to-end:** full system across claimed scale. Use as the deciding bar.
3. **Cover the relevant workload spectrum:**
   - **Steady state** under normal load.
   - **Overload:** behavior past capacity (refusals, queueing, errors) and recovery.
   - **Edge cases:** empty, single-item, max size, cold vs. warm cache.
   - **Contention:** peak concurrency, lock convoys, fairness.
   - **Fuzzed & chaos workloads:** seeded request mixes and injected faults (crashes, slow disk, dropped messages).
4. **Control the environment:** use release builds and production configs. Place load generators realistically and record unavoidable limits. When comparing systems, also follow **baseline**.
5. **Isolate runs:** run one benchmark at a time with identical data, warm-up state, and fixed seeds, because shared caches or background load contaminate timings.
6. **Measure baseline median and $\sigma$ first:** run until median, $\sigma$, IQR/MAD, and 95% CI stabilize. Treat cutting variance ($\sigma$ and tail spread) as equal to moving the median. Size run count $n$ for your exact test regime:
   - **Location (median shift):** set $\ge 1\sigma$ as the minimum detectable effect (`MDE`). Size $n$ per arm from power analysis (`d=1`, $\ge 80\%$ power -> $\sim 16\text{--}20+$ alternating runs). Test with 95% Mann-Whitney U or bootstrap CI. Never demand the sample point estimate exceed $1\sigma$, because that rejects half of true $1\sigma$ wins.
   - **Broad dispersion ($\sigma$ reduction):** never use Mann-Whitney U alone for variance cuts. Pick a target spread ratio $r = \sigma_{\text{new}}/\sigma_{\text{base}}$ upfront, and size $n \propto 1/(\ln r)^2$ (under normality, $\sim 17$ runs/arm for $r=0.5$ and $\sim 96$ for $r=0.75$; roughly $2\times$ that—$\sim 30\text{--}40$ and $\sim 175\text{--}235$—for heavy-tailed latencies). Test via **Brown–Forsythe** or a **BCa/studentized 95% bootstrap CI on $\log(\sigma_{\text{new}}/\sigma_{\text{base}}) < 0$**, with median non-regressed.
   - **Rare tails and pause spikes:** let $q$ be the tail fraction (e.g., $q=0.01$ for p99).
     - *Within-run tails:* execute $\ge 10/q$ requests per run (e.g., $\ge 1{,}000$ for p99). Compute each run's $\text{p99}-\text{p50}$, and compare across alternating runs with the location test.
     - *Rare whole-run events (rate $p$):* lengthen each run so the event recurs inside every run. If runs stay short, detecting elimination needs $n \ge 7/p$ runs/arm (~140 runs/arm at $p=5\%$ via Fisher's exact test or Brown–Forsythe).
7. **Verify the harness (red, then green):** inject a known delay or extra work to prove the harness catches regressions, because a blind harness cannot prove a win.
8. **Instrument separately and guard against noise:** run profilers in separate passes so profiler overhead never skews timing. Alternate runs round by round, verify outputs, check host load or throttling, and discard anomalous passes.
9. **Check whether the number is real:**
   - **Amdahl check (wall time = CPU + wait):** verify gains against touched wall-time fraction $f$ from off-CPU + on-CPU profiles (max speedup $1/(1-f)$). Exceeding Amdahl means a broken harness or skipped work—stop and investigate.
   - **Prove the work ran:** checksum or consume outputs so dead-code elimination or silent errors cannot fake speed.
   - **Rule out untuned ceilings:** inspect pool sizes, caches, batch sizes, GC, and debug flags on every side.
   - **Name the limiter and next $\sigma$-step:** cite the bottleneck from profiles or counters, because an unexplained number is not a valid result.
10. **Label clearly:** state metric, workload, and criterion on every benchmark.

**Done when:** the write-up records the question, metrics, environment, sampling plan, baseline median/$\sigma$/bar, results/CIs/limiters, anomalies, conclusion, and exact rerun commands. Only numbers measured this way (or set by the person) belong in acceptance criteria.

Referenced skills: `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `baseline` (`../baseline/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's benchmark-checklist and explain-the-number skills and its Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
