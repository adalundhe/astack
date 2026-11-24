---
name: explore-the-limits
description: "Research prior art, build competing implementations in parallel worktrees, benchmark them, and keep the winner. Use when no single best design or performance approach is obvious."
---

# Explore the limits

When the best implementation isn't obvious, build competing approaches and let measurements pick the winner instead of settling for the first convenient option.

1. **Research prior art** (**research-this**): survey competing implementations, algorithms, and references, ranked by source quality.
2. **Push past the obvious baseline.** Combine strong ideas from prior art, target the bottlenecks holding existing approaches back, and propose distinct candidate designs worth testing.
3. **Build candidates in parallel,** each in its own git worktree, including viable combinations (**ab-test**).
4. **Measure and compare** using profiling, **benchmarking**, and **ab-test**. Keep the measured winner and delete the rest in the same change.
5. **Don't duck hard designs.** If the winning approach is harder to build, still build it properly: make it work, then robust, then fast.
