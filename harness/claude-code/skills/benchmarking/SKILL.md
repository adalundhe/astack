---
name: benchmarking
description: "Write and run a task's benchmarks from its performance criteria, the same way as its tests: user-observable metrics, the diamond (a few micro benchmarks, a rich integration layer, chosen end-to-end benchmarks), the full spectrum (steady state, overload, edge cases, contention, fuzzed workloads, injected faults), known noise and a bar set first. Use when measuring a system, setting or checking a performance target, checking for a regression, or comparing against other systems."
---

# Benchmarking

Write and run benchmarks for a task's performance criteria.

Each benchmark follows the testing Principle (**tests-assert-behaviour**) and the shape of **full-spectrum-testing**, with one difference: a test must not depend on the machine, while a benchmark measures on one, so the machine is controlled, recorded, and the same for everything compared.

1. **Start from the criteria.** List the user-observable performance each criterion names, with units: requests per second a client gets, p50, p99 and p99.9 latency a user waits, memory the process holds, errors under load. Every benchmark traces to a criterion, or to the question an A/B must settle. Never a bare ratio such as "3x faster": without its two measurements and their spread, it says nothing.
2. **Place each benchmark on the diamond.**
   - **Micro:** one hot piece in isolation. Few, used to explain a result rather than decide one.
   - **Integration:** real components together under a realistic workload. Most measuring happens here: it is cheap enough to run on every change.
   - **End to end:** the whole system as users run it, parameterized over the scale the claim covers, from one client to the most, small data to large. Chosen sparingly, and the layer that decides.
3. **Cover the spectrum**, as it applies to each criterion:
   - steady state;
   - overload: what users get past capacity (refusals, queueing, errors) and how it recovers;
   - edge cases: empty, one, the largest, cold start against warm;
   - contention: the most concurrent clients the claim covers, lock convoys, fairness between them;
   - fuzzed workloads: request mixes generated from a seed;
   - chaos: injected faults under load, such as a node dying, a slow disk or a lost message, and what users see.
4. **Control the environment.** Production builds and configuration. Placement that measures what users get, such as the load client on a different machine from the server, set up yourself with the machines and tools you can reach; ask the person only for what only they can provide. Record any platform limit you can't remove. Against other systems, also follow **fair-benchmarks**.
5. **Isolate runs.** One benchmark at a time on a machine, so runs don't disturb each other. The same data and warm state for everything compared. Seed every generated workload and fault schedule.
6. **Know the noise.** Run the baseline enough times to estimate its spread, adding runs until each metric's 95% confidence interval of the median is narrower than the smallest difference that matters, or stops narrowing. Then set the bar before measuring anything new: a difference counts when it is larger than the baseline's spread and a Mann-Whitney U test or bootstrap interval confirms it at 95%.
7. **Red, then green.** Run each new benchmark against a build with a known regression (an injected delay or extra work) and confirm it flags it. A benchmark that can't see a known regression can't vouch for an improvement.
8. **Instrument and watch.** Counters, profiles and traces explain each result; profile in separate runs, because profilers slow what they watch. Alternate compared runs round by round, count errors and check outputs. Before and after every run, record load, power source, CPU frequency or throttling, memory pressure, disk and network, and exclude and rerun any run an anomaly hit.
9. **Explain each result.** Name what limits it from profiles and counters, not from reading the code. Rule out, with evidence, what else it could be measuring: errors, skipped or cached work, code that never ran, an untuned side, noise. A number you can't explain isn't a result yet.
10. **Name what each benchmark measures:** the metric, the workload and the criterion it serves.
11. **Write it up**, plain and complete but not long: question, metrics, environment, sampling, noise and bar, each result's median, interval and limiter, anomalies, conclusion, and the commands to rerun it. Save it where the project keeps benchmark records.

Done when every performance criterion has benchmarks on the right layer, across the spectrum that applies, each proven able to see a regression, measured against known noise and a bar set in advance, and written up.

A number measured this way, or one the person set, can be an acceptance criterion. A number picked from nowhere cannot.

<!-- Adapts pstack's benchmark-checklist and explain-the-number skills and its Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
