---
name: modularize
description: "Split monolithic packages, files, or functions into single-purpose modules behind narrow interfaces via a reviewed smallest-behavior proof of concept, dagify-batched parallel migration, and simplify-me/yagni trim—validated at every stage with vectored review. Use when code is too large or tangled to change safely."
disable-model-invocation: true
---

# Modularize

Split monolithic code into single-purpose modules that can be tested and swapped independently. Prove the pattern on the smallest slice first, migrate in reviewed batches, and trim to the minimum implementation that keeps parity.

## Design the seams

1. **Map responsibilities (**how-it-works**):** list each job, the data it owns, call graph, and where state lives (**show-the-states**).
2. **Pin behavior first:** add external behavior tests that pass before the split and stay green unchanged afterward (**tests-assert-behaviour**).
3. **Cut along domain seams, not technical layers.** Group code by job and owned data. Untangle shared mutable state and hidden state machines first (**minimize-state-stores**, **no-shared-writes**, **no-implicit-states**).
4. **Keep each module tight:** one job, owned data, a narrow interface, hidden internals, acyclic one-way dependencies, and core logic separated from outer I/O (**check-your-boundaries**). Introduce formal traits only at real boundaries, matching repo conventions.

## Execute in three reviewed stages

5. **Prove the pattern on the smallest working slice:** migrate one small cohesive unit end to end, run pinning tests, and verify parity with vectored **review** before scaling out.
6. **Migrate in parallel **dagify** batches:** plan non-overlapping batches and execute via **lead** (isolated **slates** volumes or git worktrees, read-only reviewers, and watch-and-swap clocks). Update callers per batch, separate moves from behavior changes, and verify parity and **blast-radius** seams via vectored **review** after each batch.
7. **Trim scope with **simplify-me** and **yagni**:** delete legacy paths, dead shims, and scaffolding down to the minimum implementation that preserves parity. Confirm with final vectored **review** (and **benchmarking** if latency matters), and include a Mermaid dependency diagram.

**Don't split:**

- purely by line count (a long single-purpose lookup or transition table belongs together);
- one cohesive idea across files where splitting hurts readability;
- just to add a single-implementation interface with no real boundary behind it.

Referenced skills: `how-it-works` (`../how-it-works/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `minimize-state-stores` (`../minimize-state-stores/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `no-implicit-states` (`../no-implicit-states/SKILL.md`), `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `review` (`../astack-review/SKILL.md`), `dagify` (`../dagify/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `simplify-me` (`../simplify-me/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`). Read any cited skill file before acting when its trigger applies.
