---
name: swarm-hypothesis
description: "Build competing designs in isolated workspaces, measure them, graft winning parts, and drop losers. Use when no single best design is obvious."
disable-model-invocation: true
---

# Swarm hypothesis

When no single design is clearly best, build competing approaches and measure them. Graft the strongest ideas from losing attempts onto the winner, then delete the losers.

**Skip if obvious:** when prior art or constraints pick one clear design, build it directly instead of spawning parallel variants.

1. **Research prior art (`research-this`):** survey competing implementations, algorithms, and references. Grade every source by quality.
2. **Architect distinct candidates (any number $k \ge 2$):** combine strong ideas from prior art and target the real bottlenecks. **Researchers** stay strictly read-only. They determine and architect each candidate POC (interfaces, data structures, risks, measurement plan) and hand specs to Lead for worker implementation.
3. **Build candidates via workers:**
   - **Lead:** dispatch one `astack-worker` per candidate (including hybrids) in isolated **slates** volumes or git worktrees under **lead**'s watch-and-swap clocks.
   - **Workers:** build your assigned candidate without spawning subagents. If tasked to compare options locally, prototype them sequentially in your own writable workspace.
4. **Measure, graft, and delete losing variants (`ab-test`, `benchmarking`):** compare all $k$ candidates with randomized alternating rounds and Holm–Bonferroni control. Follow `ab-test`'s graft-then-delete step.
5. **Don't duck hard designs:** if the winning approach is harder to build, still build it properly. Make it work, then robust, then fast.
6. **Clean up and ship:** log every candidate's numbers and graft choices as `decided:` in `LANES.md`. Delete all losing variants and workspaces in the same change, then send the grafted winner to **review**.

**Done when:** one grafted winner passes tests, benchmarks, and **review**, all losing workspaces are deleted, and every candidate's numbers are logged.

Referenced skills: `slates` (`../slates/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `review` (`../astack-review/SKILL.md`). Read any cited skill file before acting when its trigger applies.
