---
name: clamber
description: "Improve performance toward a goal in small, measured steps: CPU, memory (layout, page faults, cache use), disk, network, concurrency, binary or package size, bytes over the wire, or any metric named. Baseline everything, change one thing at a time, commit each gain, revert each regression. Use when a large performance gain is needed."
---

# Clamber

Improve performance toward a goal in small steps, each measured, committed, and reverted if it regresses.

## Before the first step

1. **Work, then robust, then fast.** Optimize only code that's correct and tested. The tests pass before and after every step (**tests-assert-behaviour**).
2. **Set the goal:** each metric to improve, its target, and how it's measured. CPU time; memory (peak, allocations, layout, page faults, cache misses); disk reads, writes and churn; network calls and bytes over the wire; throughput and contention under concurrency; binary or package size; or whatever the person or the work names.
3. **Reproduce the problem** with a realistic workload: the data size, history, state and concurrency users actually have. If nothing reproduces it, fix that first.
4. **Baseline everything** (**benchmarking**): every metric that matters, not only the target, so a gain in one can't hide a loss in another. Record the noise, the environment and the commands, and prove the harness can see a change.
5. **Profile and trace** to find where the time, memory, I/O and bytes actually go.
6. **Start a log** of every attempt: the idea, the change, before and after, the tests, and whether it was kept.

## Each step

Take the biggest remaining cost and ask these in strict order, acting on the first with a yes:

1. **Can we not do the work at all?**
2. **Can we do less of it?**
3. **Can we do it more efficiently?** Fewer CPU cycles and allocations, better memory layout and cache use, fewer page faults, less disk churn, fewer bytes; SIMD and vectorized code once the plain version is proven correct.
4. **Can we do it later, or elsewhere?**
5. **Can we do it in parallel?**

Then:

1. **Name the mechanism:** "defer X off the startup path, because it blocks the first response", not "try caching something".
2. **Make one change.** Don't stack untested changes.
3. **Run the tests.** Nothing users get may change (**never-trade-functionality**).
4. **Measure every baseline metric.** Keep the change only if the target moves past the noise and nothing else gets worse.
5. **Commit each kept change on its own,** with its numbers in the message, so a regression found later can be reverted alone. Revert a change that doesn't hold, in full.
6. **Log it,** kept or reverted, and go again.

When several independent ideas are waiting, try them in parallel, each in its own worktree (**ab-test**).

## Finish

- **Push past the first plateau:** try another category, combine near misses, reread the source, try something bolder. If small steps stall well short of the goal, the design may be the limit: build and measure alternatives (**explore-the-limits**).
- **Stop** when the goal is met, or when what remains can't be reached without trading functionality; put that to the person as a decision, with numbers. Don't lower the goal to meet it.
- **Report:** each metric from baseline to final, the steps kept and reverted, the log, what limits the result now, and the next idea worth trying (**prove-it**).

<!-- Adapts pstack's Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
