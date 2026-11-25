---
name: simplify-me
description: "Trim unnecessary code and complexity without losing correctness, edge cases, or speed. Use after coding or during review."
---

# Simplify me

Make recent code smaller, clearer, and easier to test. Keep correctness, edge-case handling, and performance intact.

**Skip if already minimal:** if the diff is small and clean, make no edits and say so. Churning working code adds risk without value.

1. **Check diff growth first.** Read the change end to end with fresh eyes. During PR rounds, run `astack-watch-pr diff-guard --base <ref>`, because review rounds pile on cheap patches. If review grew the diff, cut and narrow before adding code.
2. **Cut unnecessary parts.** Remove dead code, unused options, duplicated logic, single-caller wrappers, pass-through layers, and narrating comments (**comment-cop**, **yagni**).
3. **Simplify what remains.** Flatten deep nesting and split oversized functions. Replace clever tricks with plain, fast code. Keep state local or computed instead of mirrored in extra flags or caches.
4. **Improve testability.** Separate pure logic from I/O. Inject hidden inputs like clocks or globals rather than reading them deep inside helpers.
5. **Verify every cut.** Keep a simplification only when all tests pass and speed does not regress. Run **benchmarking** if latency or memory could shift, or compare close options with `ab-test`.
6. **Never drop behavior to simplify** (**never-trade-functionality**). Skip structural changes that merely look tidier.

**Done when:** `diff-guard` shows no unjustified bloat, all tests pass, and behavior is unchanged. Stop once further edits only shuffle style.

**Reply:** list what you cut or simplified, what you kept as-is, and why.

Referenced skills: `comment-cop` (`../comment-cop/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `never-trade-functionality` (`../never-trade-functionality/SKILL.md`). Read any cited skill file before acting when its trigger applies.
