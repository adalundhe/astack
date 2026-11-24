---
name: explore-the-limits
description: "Research prior art, build competing implementations in parallel worktrees, benchmark them, graft winning parts from losing variants into the winner, and delete the rest. Use when no single best design is obvious."
disable-model-invocation: true
---

# Explore the limits

When the best implementation isn't obvious, build competing approaches, measure them, graft the best ideas from losing attempts into the winner, and keep the strongest result.

1. **Research prior art** (**research-this**): survey competing implementations, algorithms, and references, graded by source quality.
2. **Push past the obvious baseline.** Combine strong ideas from prior art, target the bottlenecks holding existing approaches back, and propose distinct candidate designs worth testing.
3. **Build candidates in parallel,** each in its own git worktree, including viable combinations (**ab-test**).
4. **Measure and compare** using profiling, **benchmarking**, and **ab-test**.
5. **Graft before deleting.** Before discarding losing variants, inspect where any loser beat the winner (a sub-benchmark, tail latency, memory footprint, cleaner data structure, or simpler error path). Graft those specific improvements onto the winner, re-run tests and benchmarks to verify the hybrid beats the un-grafted winner, then delete all losing variants in the same change.
6. **Don't duck hard designs.** If the winning approach is harder to build, still build it properly: make it work, then robust, then fast.

Referenced skills: `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`). Read any cited skill file before acting when its trigger applies.
