---
name: yagni
description: "One path per job: no legacy paths, shims, adapters, bridges, deprecated aliases or dead flags unless the person or an agreed design asks for them. Use when replacing or reshaping code, when reviewing a change, or when asked to clean up legacy code."
---

# YAGNI

Keep one path per job. No legacy behaviour, bridges, shims, adapters, compatibility layers or temporary convenience code unless the person, or a design they agreed to, asks for it. You aren't going to need it.

## Start with

1. **When you replace something, move every caller and delete the old one in the same change.** Nothing new may depend on a path being deleted.
2. **Rewrite tests to the new contract,** and delete tests that only pinned the old one.
3. **Find everything that uses a path before removing it:** code, configuration, scripts, docs, other repositories, wire formats and stored data (**blast-radius**). Breaking people outside the project is the person's call (**decisions-in-plain-words**).
4. **It's done when** the tests of everything that used it pass, and the scenario the old path served runs on the new one.

## Watch for

- old paths kept beside new ones, and fallbacks to an old implementation;
- adapters and wrappers that only translate between old and new;
- deprecated aliases and re-exports;
- flags and settings for behaviour that no longer exists;
- parameters kept "for compatibility";
- tests that pin old behaviour.

**The test:** does anything still need this path, and did the person ask to keep it?

## When it doesn't fit

- a shim, alias, fallback or flag that the person, or a design they agreed to, asks for, cited where, with a condition for removing it.

<!-- Adapts pstack's migrate-callers-then-delete-legacy-apis principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
