---
name: swarm-hypothesis
description: "Research prior art, build competing implementations in parallel isolated Slates VFS volumes (preferred when available) or git worktrees, benchmark them, graft winning parts from losing variants into the winner, and delete the rest. Use when no single best design is obvious."
---

# Swarm hypothesis

When the best implementation isn't obvious, build competing approaches, measure them, graft the best ideas from losing attempts into the winner, and keep the strongest result.

1. **Research prior art** (**research-this**): survey competing implementations, algorithms, and references, graded by source quality.
2. **Push past the obvious baseline.** Combine strong ideas from prior art, target the bottlenecks holding existing approaches back, and propose distinct candidate designs worth testing.
3. **Build candidates in parallel,** dispatching one `astack-worker` per candidate in its own **slates** in-memory VFS volume (`https://github.com/hyper-light/slates`, preferred when available) or **git worktree**, including viable combinations (**ab-test**). Enforce **lead**'s watch/swap clocks on all parallel workers and reviewers (`LANES.md` + `astack-status` every `check_in_minutes`, wind-down reminder, fresh successor with reset timers on overdue runs).
4. **Measure and compare** using profiling, **benchmarking**, and **ab-test**.
5. **Graft before deleting.** Before discarding losing variants, inspect where any loser beat the winner (a sub-benchmark, tail latency, memory footprint, cleaner data structure, or simpler error path). Graft those specific improvements onto the winner, re-run tests and benchmarks to verify the hybrid beats the un-grafted winner, then delete all losing variants in the same change.
6. **Don't duck hard designs.** If the winning approach is harder to build, still build it properly: make it work, then robust, then fast.

Referenced skills: `research-this` (`../research-this/SKILL.md`), `slates` (`../slates/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`). Read any cited skill file before acting when its trigger applies.
