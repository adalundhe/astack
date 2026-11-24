---
name: simplify-me
description: "Trim unnecessary code and complexity from recent changes or code under review while keeping correctness, edge cases, and performance intact. Use after implementation, before review, or during review."
---

# Simplify me

Make recently written code (or code under review) smaller, clearer, and easier to test without losing correctness, edge-case handling, or performance.

1. **Read it end to end** with fresh eyes as if you didn't write it.
2. **Cut unnecessary parts:** dead code, unused options/parameters, duplicated logic, single-caller wrappers, single-implementation interfaces, pass-through layers, and comments the code can replace (**comment-cop**, **yagni**).
3. **Make what remains straightforward:** flatten deep nesting, break up oversized functions, replace clever tricks with plain equally fast code, use standard-library primitives, and keep state local or computed (**minimize-state-stores**, **no-implicit-states**).
4. **Improve testability:** separate pure logic from I/O and inject hidden inputs like clocks or globals (**check-your-boundaries**).
5. **Verify every simplification:** keep changes only if all tests pass and robustness/performance don't regress. Benchmark if speed or memory could shift (**benchmarking**), and run **ab-test** if two options look close.
6. **Never drop behavior to simplify** (**never-trade-functionality**), and don't add structure that merely looks tidier.
7. **Summarize** what you cut or simplified, what you intentionally kept as-is, and why.

Referenced skills: `comment-cop` (`../comment-cop/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `minimize-state-stores` (`../minimize-state-stores/SKILL.md`), `no-implicit-states` (`../no-implicit-states/SKILL.md`), `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `never-trade-functionality` (`../never-trade-functionality/SKILL.md`). Read any cited skill file before acting when its trigger applies.
