---
name: swarm-hypothesis
description: "Research prior art, build competing implementations in parallel isolated workspaces, benchmark them, graft winning parts from losing variants into the winner, and delete the rest. Use when no single best design is obvious."
disable-model-invocation: true
---

# Swarm hypothesis

When the best implementation isn't obvious, build competing approaches, measure them, graft the best ideas from losing attempts into the winner, and keep the strongest result.

1. **Research prior art (**research-this**):** survey competing implementations, algorithms, and references, graded by source quality.
2. **Push past the obvious baseline.** Combine strong ideas from prior art, target the bottlenecks holding existing approaches back, and propose distinct candidate designs worth testing.
3. **Build candidates in parallel.** Dispatch one `astack:worker` per candidate (including viable combinations, per **ab-test**) using **lead**'s isolated workspaces (**slates** or git worktrees) and watch-and-swap clocks.
4. **Measure and compare** using profiling, **benchmarking**, and **ab-test**.
5. **Graft before deleting.** Before discarding losers, check where any loser beat the winner (sub-benchmark, tail latency, memory, cleaner data shape, or simpler error path). Graft those wins onto the winner and re-verify tests and benchmarks. Then delete all losing variants in the same change.
6. **Don't duck hard designs.** If the winning approach is harder to build, still build it properly: make it work, then robust, then fast.
