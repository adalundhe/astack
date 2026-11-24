---
name: ab-test
description: "Settle a choice between designs, implementations or settings by measuring them: each variant in its own worktree, combinations included, measured with the benchmarking skill at the extremes, then decide and proceed. Use whenever measuring could settle a choice between architectures, implementations or configurations."
---

# A/B test

Settle a choice between options by measuring each the same way.

1. **Measure with benchmarking.** Its metrics, environment, baseline noise, bar, instruments, runs, anomalies and write-up apply to every variant.
2. **Variants.** Give each its own worktree from the same base commit, or its own volume (such as a Slates volume) when it needs separate data. When changes can coexist, also build the combination (A, B and A+B), because gains don't always add. Each variant works and passes its tests before it is measured.
3. **Extremes.** Run the scale the claim covers at both ends, and force each variant's failure modes: a design that wins in the middle often loses at an edge.
4. **Alternate.** One variant at a time, round by round (base, A, B, A+B, base, ...), with as many runs each as the baseline needed.
5. **Decide and proceed.** Take the variant that clears the bar on the deciding metric without losing past the bar on another. If none clears it, take the simplest. Record the decision in the write-up, delete the losers in the same change, and carry on.

<!-- Adapts pstack's benchmark-checklist skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
