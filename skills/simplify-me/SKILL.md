---
name: simplify-me
description: "Simplify code you just wrote or are reviewing: less of it, clearer, easier to test, without giving up correctness, robustness, performance, efficiency or scalability. Use after finishing an implementation, before handing it to review, and when reviewing one."
---

# Simplify me

Make the code you just wrote, or are reviewing, smaller, clearer and easier to test, without giving up correctness, robustness, performance, efficiency or scalability.

1. **Reread it whole,** as someone seeing it for the first time.
2. **Cut what isn't needed:** dead code, unused options and parameters, duplicated logic, wrappers with one caller, interfaces with one implementation, layers that only pass data through, and comments the code could replace (**comment-cop**, **yagni**).
3. **Make the rest plainer:** flatten deep nesting, split long functions, replace clever code with plain code that's as fast, use what the language or standard library already has, and keep state local or computed (**minimize-state-stores**, **no-implicit-states**).
4. **Make it easy to test:** separate logic from I/O, and pass in hidden inputs such as clocks and globals (**check-your-boundaries**).
5. **Keep a change only if the tests still pass** and nothing gets slower or less robust. Measure where speed or memory could change (**benchmarking**); when unsure between two versions, try both (**ab-test**).
6. **Don't simplify by dropping behaviour** (**never-trade-functionality**), or by adding structure that only looks tidier.
7. **Report** what you cut or reshaped, and what you left as it was, and why.
