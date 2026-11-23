---
name: ab-test
description: "Settle a choice between designs, implementations or settings by measuring them: quantifiable metrics, the best-suited environment set up without asking, baseline noise first, a meaningful-improvement bar from that noise, one worktree per variant and combination, production builds, anomalies recorded, a plain write-up, then the decision. Use whenever measuring could settle a choice between architectures, implementations or configurations."
---

# A/B test

Measure every option the same way, decide from the result, and carry on.

**Why:** reasoning about which design is better is not evidence, and a number means something only against the noise it was measured in.

1. **Metrics.** Pick metrics that each stand on their own, with a unit: requests per second, p50, p99 and p99.9 latency in ms, CPU seconds, peak memory in MB, allocations, bytes written, errors. Say which direction is better and which metric wins when they disagree. Never a bare ratio such as "3x faster": without its two measurements and their spread, it says nothing.
2. **Environment.** From the requirement, decide where each part runs so the test measures what users get: production builds, the scale the claim covers at both ends (one client and the most, a small machine and a large one, idle and loaded), and placement that doesn't skew results, such as the load client on a different machine from the server. Set it up yourself with the machines and tools you can reach: remote runners, SSH hosts, cloud CLIs already signed in, containers. Record any platform limit you can't remove. Ask the person only if the test can't run without something only they can provide.
3. **Baseline noise.** Run the unchanged system in that environment at least five times (fewer can't estimate spread), and keep adding runs until the 95% confidence interval of each metric's median is narrower than the smallest difference that would change the decision, or stops narrowing. Record the median, the spread and the interval.
4. **The bar.** Before measuring any variant, set what counts as meaningful, in each metric's units: a difference larger than the baseline's run-to-run spread that a Mann-Whitney U test or a bootstrap interval confirms at 95% confidence. A bar set after the results bends to them.
5. **Variants.** Give each variant its own worktree from the same base commit, or its own volume (such as a Slates volume) when it needs separate data. When two changes can coexist, also build the combination (A, B and A+B), because gains don't always add. Each variant must work and pass its tests before it is measured.
6. **Instruments.** Add the counters, profiling, tracing and system monitoring that explain each result. Profile in separate runs, because profilers slow the work they watch.
7. **Runs.** Production builds and configuration, one variant at a time, never two at once. Alternate them round by round (base, A, B, A+B, base, ...) so drift hits all alike, with as many runs per variant as the baseline needed. Count errors and check outputs: a refused or wrong request is often the fastest.
8. **Anomalies.** Before and after every run, record load, power source, CPU frequency or throttling, memory pressure, disk space and network reachability. Mark, exclude and rerun any run hit by an anomaly, such as a laptop switching to battery, the network dropping, or another job starting.
9. **Write-up.** Plain and complete, not long: the question; metrics and units; environment (machines, builds, configuration, placement); sampling (runs per variant, order, warm-up, exclusions); baseline noise and the bar; a table of each variant's median and interval per metric; anomalies; the decision and why; the commands to rerun it. Save it where the project keeps benchmark records, or in the program folder, and put the key numbers in the commit message, so anyone can check and rerun it.
10. **Decide and proceed.** Take the variant that clears the bar on the deciding metric without losing past the bar on another. If none clears it, take the simplest. Delete the losers in the same change (two paths cost upkeep and hide which one runs), then carry on with the work.

<!-- Adapts pstack's benchmark-checklist and explain-the-number skills and its Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
