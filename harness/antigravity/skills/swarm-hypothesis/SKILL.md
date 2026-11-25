---
name: swarm-hypothesis
description: "Build competing designs in isolated workspaces, measure them, graft winning parts, and drop losers. Use when no single best design is obvious."
disable-model-invocation: true
---

# Swarm hypothesis

When no single design is clearly best, build competing approaches and measure them. Graft the strongest ideas from losing attempts onto the winner, then delete the losers.

**Skip if obvious:** when prior art or constraints already pick one clear design, build it directly instead of spawning parallel variants.

1. **Research prior art (**research-this**):** survey competing implementations, algorithms, and references. Grade every source by quality.
2. **Push past the obvious baseline:** combine strong ideas from prior art and target the bottlenecks holding existing options back. Propose distinct candidate designs worth testing.
3. **Build candidates cleanly:**
   - **Lead:** dispatch one `astack-worker` per candidate (including promising hybrids) in isolated **slates** volumes or git worktrees under **lead**'s watch-and-swap clocks.
   - **Workers / Researchers:** propose candidates or prototype them sequentially inside your own workspace without spawning subagents.
4. **Measure and compare:** profile each candidate under the same workload using **benchmarking** and **ab-test**.
5. **Graft before deleting:** inspect where any loser beat the winner—sub-benchmarks, tail latency, memory, cleaner data shape, or simpler error handling. Graft those wins onto the winner, because the second-place design often solves one edge better than the overall winner. Re-verify all tests and benchmarks.
6. **Don't duck hard designs:** if the winning approach is harder to build, still build it properly. Make it work, then robust, then fast.
7. **Clean up and ship:** log every candidate's numbers and the graft decisions as `decided:` in `LANES.md`. Delete all losing variants and workspaces in the same change, then send the grafted winner to **review**.

**Done when:** one grafted winner passes tests, benchmarks, and **review**, all losing workspaces are deleted, and every candidate's numbers are logged.

Referenced skills: `research-this` (`../research-this/SKILL.md`), `slates` (`../slates/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `review` (`../astack-review/SKILL.md`). Read any cited skill file before acting when its trigger applies.
