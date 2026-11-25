---
name: no-bolt-ons
description: "Integrate new requirements cleanly into the existing design instead of adding flags, copies, or wrappers. Use when adding features to existing code or reviewing special-case changes."
disable-model-invocation: true
---

# No bolt-ons

Integrate each new requirement as if it belonged in the design from day one, because special-case flags and wrappers double maintenance paths.

## Start with

1. **Understand the existing design first** (**how-it-works**)—read everything the requirement touches.
2. **Design from first principles:** structure the code the way you'd build it from scratch with this requirement included.
3. **Update every reference:** types, callers, tests, docs, examples, and architecture notes. Remove all traces of the superseded design (**yagni**).
4. **Ship incrementally:** design the full shape up front, then land it in verifiable steps.

## Watch for

- mode flags or boolean switches splitting an existing code path in two;
- special-case checks for one caller or input repeated across files;
- parallel copies (`process_v2`, `handle_new`) or wrapper functions patching around existing logic;
- new parameters threaded through layers that don't use them;
- types, docs, or tests still describing the pre-change design.

**The test:** if this requirement had existed from day one, would the code look like this?

## When it doesn't fit

- narrow, localized bug fixes scoped to the fault boundary (`fix-it`); fix the defect cleanly and log broader structural cleanup separately;
- a genuinely separate concern that belongs in its own module with its own callers;
- a requested migration behind a proper feature flag (**no-hidden-config**) with an explicit removal condition;
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** point to the parallel copy, mode flag, or caller-specific branch, and show how folding it into the core abstraction removes the split.

Referenced skills: `how-it-works` (`../how-it-works/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `no-hidden-config` (`../no-hidden-config/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's redesign-from-first-principles principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
