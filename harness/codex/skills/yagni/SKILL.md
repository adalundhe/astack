---
name: yagni
description: "Keep one code path per job: migrate callers and delete legacy paths, shims, adapters, aliases, and dead flags together unless explicitly requested. Use when replacing code, reviewing changes, or cleaning up."
---

# YAGNI

Keep one path per job. Don't add or retain legacy paths, shims, adapters, compatibility layers, or dead flags unless the person—or an agreed design—explicitly asks for them.

## Start with

1. **Migrate and delete together:** when replacing a path, update every caller and remove the old code in the same change. Nothing new may depend on a deprecated path.
2. **Update tests to the new contract** and delete tests that only pinned the old behavior.
3. **Check all consumers before deleting:** code, config, scripts, docs, other repos, wire formats, and stored data (**blast-radius**). Breaking external consumers is the person's call (**decisions-in-plain-words**).
4. **Done when** all consumer tests pass and the scenario served by the old path runs cleanly on the new one.

## Watch for

- old implementations left beside new ones or fallback branches to legacy code;
- pass-through wrappers or adapters translating between old and new shapes;
- deprecated aliases and re-exports;
- flags or config keys for removed behavior;
- unused parameters kept "for compatibility";
- tests pinning retired behavior.

**The test:** does anything still need this path, and did the person ask to keep it?

## When it doesn't fit

- a shim, alias, fallback, or flag explicitly requested by the person or an agreed design, citing where it was approved and the condition for removing it.

Referenced skills: `blast-radius` (`../blast-radius/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's migrate-callers-then-delete-legacy-apis principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
