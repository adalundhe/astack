---
name: never-trade-functionality
description: "A faster version must do everything the slower one did: no stale, approximate, late or missing results, no weaker guarantees. Use when a speedup or memory cut changes what users get, or before proposing a lean, deferred or approximate variant."
---

# Never trade functionality for speed

We do not compromise functionality for performance. A faster version keeps every value as exact and as fresh, every guarantee as strong, and every failure as visible.

**Why:** people depend on what the system does. A faster answer that is wrong, stale or less safe is a regression.

- Never build or recommend a trade: weaker durability, checks turned off, stale or approximate values. If speed needs one, stop and report it as a decision, with numbers.
- Push everything else hard, in this order: skip work that isn't needed, do less of it, do it more efficiently, do it elsewhere or later, do it in parallel.
- Robustness is functionality. Add no new way to stall, lose data or crash.
- Make the uncached path fast before adding a cache. A cache is a second copy of the truth that goes stale and hides the real fault.
- Show that nothing reads what you leave out. Don't assume it.
- If a target can't be met with everything intact, report the best number that keeps everything, and what limits it.
