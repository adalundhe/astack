---
name: no-bolt-ons
description: "Fold a new requirement into the design as if it had always been there, instead of adding special cases, flags and parallel paths. Use when adding a requirement to existing code, and when reviewing a change that adds special cases."
---

# No bolt-ons

Design a new requirement in as if it had always been there, instead of bolting it on.

## Start with

1. **Read everything it touches,** and understand the current design first (**how-it-works**).
2. **Build what you'd build from scratch** with the requirement there from the start.
3. **Carry it through every reference:** types, callers, tests, docs, examples, and the recorded reasons for the old design. Nothing describes a design that's gone (**yagni**).
4. **Design the whole, deliver it in steps,** each ending in a state that can be checked.

## Watch for

- a flag or mode that splits a path in two;
- a special case for one caller or one input, repeated wherever it matters;
- a parallel copy of something that exists (`process_v2`, `handle_new`), or a wrapper that patches one behaviour of another;
- a new parameter threaded through layers that don't use it;
- types, docs or tests that still describe the design before the requirement.

**The test:** if this requirement had been there from the start, would the code look like this?

## When it doesn't fit

- a requirement that's truly its own concern, in its own module with its own callers, not a special case of an existing path;
- a temporary path the person or an agreed design asked for, such as a migration or a staged rollout behind a proper feature flag (**no-hidden-config**), with a condition for removing it;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

<!-- Adapts pstack's redesign-from-first-principles principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
