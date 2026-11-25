---
name: ab-test
description: "Benchmark isolated design, code, or config variants across extreme workloads and graft winning ideas. Use whenever measurement can settle a choice."
disable-model-invocation: true
---

# A/B test

Settle a choice between options by measuring each the same way.

1. **Follow benchmarking.** Use **benchmarking** for metrics, environment control, baseline noise, statistical bars, instrumentation, anomaly checks, and write-ups.
2. **Isolate variants.** Build each variant from the same base commit in its own workspace (**slates** volume or git worktree with separate mutable data). Keep workspaces isolated, because shared caches or mutated stores skew later runs. For parallel builds, Lead dispatches one `astack-worker` per variant under **lead**'s workspaces and watch-and-swap clocks. Test viable combinations (A+B). Verify tests pass first, because broken code can look artificially fast.
3. **Test the extremes.** Run both ends of the scale the claim covers. Trigger each variant's failure modes, because designs that win in the middle often lose at the edges.
4. **Alternate runs.** Run one variant at a time, round by round (base, A, B, A+B, base, ...). Match the baseline round count. Never run back-to-back blocks, because host drift and thermal throttling bias cooler runs.
5. **Pick, graft, and clean up.** Pick the variant that clears the deciding bar without regressing other metrics. Pick the simplest if none clears it. Check if any loser won on a secondary metric, edge case, or clarity. Graft worthwhile pieces onto the winner, then rerun tests and benchmarks.

**Done when:** the winner and proof are logged as `decided:`. Losing variants are deleted in the same change, and loser workspaces are torn down.

Referenced skills: `benchmarking` (`../benchmarking/SKILL.md`), `slates` (`../slates/SKILL.md`), `lead` (`../astack-lead/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's benchmark-checklist and arena skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
