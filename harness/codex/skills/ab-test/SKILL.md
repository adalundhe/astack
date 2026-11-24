---
name: ab-test
description: "Settle design, implementation, or config choices by benchmarking variants in separate worktrees (including combinations) across extreme workloads, grafting any winning ideas before deleting losers. Use whenever measurement can settle a choice."
---

# A/B test

Settle a choice between options by measuring each the same way.

1. **Follow benchmarking.** Use **benchmarking** for metrics, environment control, baseline noise, statistical bar, instrumentation, anomaly checks, and the write-up.
2. **Isolate variants.** Build each variant in its own git worktree from the same base commit (and give each its own data directory or volume if it mutates state). When changes can coexist, also test the combination (A, B, and A+B), since gains don't always add. Every variant must work and pass its tests before you measure it.
3. **Test the extremes.** Run both ends of the scale the claim covers and trigger each variant's failure modes. Designs that win in the middle often lose at the edges.
4. **Alternate runs.** Run one variant at a time, round by round (base, A, B, A+B, base, ...), for as many rounds as the baseline needed.
5. **Pick, graft, and clean up.** Pick the variant that clears the bar on the deciding metric without regressing past the bar on another (or the simplest if none clears it). Before deleting losers, check if any loser won on a secondary metric, edge case, or design clarity—graft worthwhile pieces onto the winner and re-verify tests and benchmarks. Record the decision in the write-up, delete the losing variants in the same change, and move on.

Referenced skills: `benchmarking` (`../benchmarking/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's benchmark-checklist and arena skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
