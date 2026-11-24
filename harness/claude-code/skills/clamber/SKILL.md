---
name: clamber
description: "Iteratively improve performance (CPU, memory, I/O, network, concurrency, or size) in small measured steps: baseline everything, change one thing at a time, commit gains, revert regressions. Use when significant optimization is needed."
---

# Clamber

Improve performance toward a target in small, measured steps—committing each gain and reverting anything that regresses.

## Before the first step

1. **Work, then robust, then fast.** Only optimize code that already works and passes its tests. Tests must pass before and after every step (**tests-assert-behaviour**).
2. **Define the target.** Specify each metric to improve, the target number, and how it's measured (CPU, peak memory/allocations/cache misses/page faults, disk I/O, network calls/wire bytes, concurrent throughput/contention, binary/package size, or any requested metric).
3. **Reproduce realistically.** Use realistic data sizes, history, state, and concurrency. If you can't reproduce the bottleneck, fix the workload first.
4. **Baseline every important metric** (**benchmarking**), not just the primary target, so a win in one metric can't hide a regression in another. Record noise, environment, and commands, and verify the harness detects regressions.
5. **Profile and trace** to see where time, memory, I/O, or bytes actually go.
6. **Keep an experiment log** of every attempt: hypothesis, change, before/after numbers, test status, and kept/reverted outcome.

## Each step

Pick the largest remaining bottleneck and ask these in strict order, acting on the first "yes":

1. **Can we skip the work entirely?**
2. **Can we do less of it?**
3. **Can we do it more efficiently?** Fewer CPU cycles and allocations, better cache/memory layout, fewer page faults, less disk churn, fewer bytes; SIMD/vectorization only after the plain version is proven correct.
4. **Can we defer it or move it off the hot path?**
5. **Can we parallelize it?**

Then:

1. **State the mechanism:** e.g. "defer X off startup because it blocks first response", not "try caching".
2. **Make one isolated change.** Don't stack untested ideas.
3. **Run the tests.** User-visible behavior must stay identical (**never-trade-functionality**).
4. **Re-measure all baseline metrics.** Keep the change only if the target improves beyond noise without regressing other metrics.
5. **Commit or revert cleanly.** Commit each kept win on its own with numbers in the commit message so later regressions can be bisected/reverted individually. Revert failed attempts completely.
6. **Log the attempt** and repeat.

If you have several independent ideas, test them in parallel in separate worktrees (**ab-test**).

## Finish

- **Break through plateaus.** If incremental tweaks stall well short of the goal, try another optimization category, combine near misses, reread the hot path, or prototype alternative architectures (**explore-the-limits**).
- **Know when to stop.** Stop when you hit the target. Before concluding further gains require trading functionality, run **research-this** and **explore-the-limits** to verify no compliant design exists; only then present the best compliant result, what limits it, and the trade-off with numbers to the person (**never-trade-functionality**, **decisions-in-plain-words**). Never relax the goal to declare victory.
- **Report:** baseline vs. final for every metric, steps kept and reverted, the full log, the current bottleneck, and the best next lead (**prove-it**).

<!-- Adapts pstack's Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
