---
name: yagni
description: "Keep one code path per job: migrate callers and delete legacy paths, shims, and dead flags together. Use when replacing code, reviewing, or cleaning up."
disable-model-invocation: true
---

# YAGNI

Keep one path per job, because parallel legacy paths double surface area and drift silently. Never add or keep legacy paths, shims, adapters, compatibility layers, or dead flags unless explicitly requested.

## Start with

1. **Migrate and delete together:** when replacing a path, update every caller and delete the old code in the same change. Nothing new may depend on a deprecated path.
2. **Update tests to the new contract:** migrate relevant tests and delete tests that only pinned retired behavior.
3. **Check every consumer before deleting:** audit code, config, scripts, docs, other repos, wire formats, and stored data (**blast-radius**). Breaking external consumers is the person's call (**decisions-in-plain-words**).
4. **Verify clean cutover:** run all consumer tests and confirm the old scenario runs cleanly on the new path.

## Watch for

- old implementations left beside new ones or fallback branches to legacy code;
- pass-through wrappers or adapters translating between old and new shapes;
- deprecated aliases and re-exports;
- flags or config keys for removed behavior;
- unused parameters kept "for compatibility";
- tests pinning retired behavior.

**The test:** does anything still need this path, and did the person ask to keep it?

## When it doesn't fit

- a shim, alias, fallback, or flag explicitly requested in writing, citing where it was approved and when to remove it;
- temporary expand-and-contract compatibility so running workloads and rollbacks survive a deploy across releases (**safe-to-deploy**). Pair it with an explicit retirement release or runbook step.

**Showing it:** grep confirms zero live callers of retired paths and all consumer tests pass on the single remaining path.

Referenced skills: `blast-radius` (`${CLAUDE_SKILL_DIR}/../blast-radius/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `safe-to-deploy` (`${CLAUDE_SKILL_DIR}/../safe-to-deploy/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's migrate-callers-then-delete-legacy-apis principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
