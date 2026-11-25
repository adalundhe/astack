---
name: simplify-me
description: "Trim unnecessary code and complexity from recent changes or code under review while keeping correctness, edge cases, and performance intact. Use after implementation, before review, or during review."
disable-model-invocation: true
---

# Simplify me

Make recently written code (or code under review) smaller, clearer, and easier to test without losing correctness, edge-case handling, or performance.

1. **Check diff growth and read end to end** with fresh eyes. During PR rounds, run `astack-watch-pr diff-guard`: if review grew the diff, cut and narrow first before adding code.
2. **Cut unnecessary parts:** remove dead code, unused options, duplicated logic, single-caller wrappers, pass-through layers, and narrating comments (**comment-cop**, **yagni**).
3. **Make what remains straightforward:** flatten deep nesting, split oversized functions, replace clever tricks with plain fast code, and keep state local or computed (**minimize-state-stores**, **no-implicit-states**).
4. **Improve testability:** separate pure logic from I/O and inject hidden inputs like clocks or globals (**check-your-boundaries**).
5. **Verify every simplification:** keep changes only if all tests pass and robustness/performance don't regress. Benchmark if speed or memory could shift (**benchmarking**), and run **ab-test** if two options look close.
6. **Never drop behavior to simplify** (**never-trade-functionality**), and don't add structure that merely looks tidier.
7. **Summarize** what you cut or simplified, what you intentionally kept as-is, and why.

Referenced skills: `comment-cop` (`../comment-cop/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `minimize-state-stores` (`../minimize-state-stores/SKILL.md`), `no-implicit-states` (`../no-implicit-states/SKILL.md`), `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `never-trade-functionality` (`../never-trade-functionality/SKILL.md`). Read any cited skill file before acting when its trigger applies.
