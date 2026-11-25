---
name: ab-test
description: "Settle design, implementation, or config choices by benchmarking variants in separate workspaces (including combinations) across extreme workloads, grafting any winning ideas before deleting losers. Use whenever measurement can settle a choice."
---

# A/B test

Settle a choice between options by measuring each the same way.

1. **Follow benchmarking.** Use **benchmarking** for metrics, environment control, baseline noise, statistical bar, instrumentation, anomaly checks, and the write-up.
2. **Isolate variants.** Build each variant from the same base commit in its own isolated workspace (**slates** volume or git worktree, with separate mutable data directories). When building in parallel, dispatch one `astack-worker` per variant under **lead**'s workspaces and watch-and-swap clocks. Test viable combinations (A+B), and verify tests pass before measuring.
3. **Test the extremes.** Run both ends of the scale the claim covers and trigger each variant's failure modes, because designs that win in the middle often lose at the edges.
4. **Alternate runs.** Run one variant at a time, round by round (base, A, B, A+B, base, ...), for as many rounds as the baseline needed.
5. **Pick, graft, and clean up.** Pick the variant that clears the deciding bar without regressing other metrics (or the simplest if none clears it). Before deleting losers, check if any loser won on a secondary metric, edge case, or clarity. Graft worthwhile pieces onto the winner and re-verify tests and benchmarks. Record the decision, delete losing variants in the same change, and move on.

Referenced skills: `benchmarking` (`../benchmarking/SKILL.md`), `slates` (`../slates/SKILL.md`), `lead` (`../astack-lead/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's benchmark-checklist and arena skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
