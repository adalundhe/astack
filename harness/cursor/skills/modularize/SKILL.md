---
name: modularize
description: "Split monolithic code into single-purpose modules via a proof slice, batched migration, and parity trim. Use when code is too large or tangled to change safely."
disable-model-invocation: true
---

# Modularize

Split monolithic code into single-purpose modules that test and swap cleanly. Prove one small slice first, migrate in reviewed batches, and trim to minimum parity.

## Design the seams (Workers and Lead)

1. **Map responsibilities (**how-it-works**):** list each job, owned data, call graph, and where state lives (`show-the-states`).
2. **Pin behavior first:** add external behavior tests (`tests-assert-behaviour`) that stay green unchanged, because unpinned moves hide regressions.
3. **Cut along domain seams, not technical layers.** Group code by job and owned data. Untangle shared mutable state and hidden state machines first (`minimize-state-stores`, `no-shared-writes`, `no-implicit-states`).
4. **Keep each module tight:** give each module one job, owned data, a narrow interface, and hidden internals. Enforce acyclic dependencies, isolate I/O (`check-your-boundaries`), and add traits only at real boundaries.

## Execute in three reviewed stages (Lead only; workers use Steps 1–4)

5. **Prove the pattern on the smallest slice:** migrate one cohesive unit end to end and run pinning tests. Confirm parity with vectored **review** first, because a flawed seam multiplies rework across batches.
6. **Migrate in parallel **dagify** batches:** plan non-overlapping batches and execute via **lead** with **slates** workspaces and watch-and-swap orchestration. Update callers per batch, separate moves from behavior edits, and verify `blast-radius` seams via **review**.
7. **Trim scope with **simplify-me** and `yagni`:** delete legacy paths, dead shims, and scaffolding down to parity. Confirm with final vectored **review** (`benchmarking` if latency matters) and add a Mermaid dependency diagram.

**Don't split:**

- purely by line count (a long single-purpose lookup or transition table belongs together);
- one cohesive idea across files where splitting hurts readability;
- just to add a single-implementation interface with no real boundary behind it.

**Done when:** pinning tests pass unchanged, shims are trimmed, final **review** passes, and a Mermaid diagram is included.

Referenced skills: `how-it-works` (`../how-it-works/SKILL.md`), `review` (`../astack-review/SKILL.md`), `dagify` (`../dagify/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `simplify-me` (`../simplify-me/SKILL.md`). Read any cited skill file before acting when its trigger applies.
