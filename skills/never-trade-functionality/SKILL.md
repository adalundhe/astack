---
name: never-trade-functionality
description: "A faster version must do everything the slower one did: no stale, approximate, late or missing results, no weaker guarantees. Use when writing or reviewing a speedup or memory cut, or before proposing a lean, deferred or approximate variant."
---

# Never trade functionality for speed

A faster version does everything the slower one did: every value as exact and as fresh, every guarantee as strong, every failure as visible.

## Start with

1. **Find speed in this order** (**clamber**): skip work that isn't needed, do less of it, do it more efficiently, do it elsewhere or later, do it in parallel.
2. **Keep robustness:** add no new way to stall, lose data or crash.
3. **Make the plain path fast before adding a cache** (**minimize-state-stores**).
4. **Show that nothing reads what you leave out.** Don't assume it.
5. **If a target can't be met with everything intact,** report the best number that keeps everything, and what limits it.
6. **If speed truly needs a trade, don't make it:** put it to the person as a decision, with numbers (**decisions-in-plain-words**).

## Watch for

Writes acknowledged before they're safe; checks or validation turned off; stale, approximate, sampled or truncated results; dropped fields or features; errors swallowed to save time; lower precision; work deferred where users then see the gap.

**The test:** does every user still get every value, as exact and as fresh, with every guarantee and every error?

## When it doesn't fit

- removing work that nothing reads, once that's shown;
- a trade the person decided, on record with its numbers;
- an approximation the requirement asks for, such as an estimate or a progress indicator.

**Showing it:** run the old and new versions on the same inputs, failures and edge cases included, and compare what users get.
