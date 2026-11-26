---
name: ab-test
description: "Benchmark isolated design, code, or config variants across extreme workloads and graft winning ideas. Use whenever measurement can settle a choice."
disable-model-invocation: true
---

# A/B test

Settle a choice across any number of options ($k \ge 2$) by measuring each the same way.

1. **Follow benchmarking.** Use **benchmarking** for metrics, environment control, baseline noise, statistical bars, instrumentation, anomaly checks, and write-ups.
2. **Isolate every variant ($k \ge 2$).** Test baseline plus any number of candidates and hybrids (`base, V1, V2, ..., Vk`). Build each from the same base commit in its own **slates** volume or git worktree with separate mutable data. Shared caches or mutated stores skew later runs. For parallel builds, Lead dispatches one `astack-worker` per variant under **lead**'s watch-and-swap clocks. Verify tests pass first, because broken code can look artificially fast.
3. **Test the extremes.** Run both ends of the scale the claim covers. Trigger each variant's failure modes, because designs that win in the middle often lose at the edges.
4. **Alternate runs and control multiple comparisons.** Follow **benchmarking**'s host quiescence, serialization, noise-band retry, and post-benchmark **review** rules (and **baseline** for multi-host parity). Run variants in randomized alternating rounds—never back-to-back blocks. For $m$ comparisons across $>2$ arms, apply **Holm–Bonferroni**: sort $p_{(1)} \le \dots \le p_{(m)}$ and require $p_{(j)} \le \alpha / (m - j + 1)$. For wide sweeps, run Kruskal–Wallis or a permutation test before promoting finalists.
5. **Pick, graft, and clean up (canonical graft-then-delete).** Pick the variant that clears the Holm-adjusted bar without regressing other metrics. Pick the simplest if none clears it. Check every loser for secondary wins (tail latency, memory, edge cases, cleaner data shape, simpler error handling). Graft worthwhile pieces onto the winner, then rerun tests and benchmarks. Delete all losing variants and tear down loser workspaces in the same change.

**Done when:** the winner and proof are logged as `decided:`. Losing variants are deleted in the same change, and loser workspaces are torn down.

Referenced skills: `benchmarking` (`../benchmarking/SKILL.md`), `slates` (`../slates/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `review` (`../astack-review/SKILL.md`), `baseline` (`../baseline/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's benchmark-checklist and arena skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
