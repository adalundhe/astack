---
name: never-trade-functionality
description: "Keep every behaviour intact while making things faster: no stale, approximate, late or missing results, no weaker correctness or durability, no lost robustness. Use when a speedup or memory cut changes what users get, and before you propose a lean, deferred or approximate variant."
---

# Never trade functionality for speed

A performance change keeps everything the system does exactly as it was: every value as exact and as fresh, every guarantee as strong, every failure as visible.

Ada's words: "We do not compromise functionality for the sake of performance like this. Period."

**Why:** people rely on what the system does, not on how fast it does it. A faster answer that is wrong, stale or less safe is a regression.

- **Don't build the trade, and don't recommend it.** Weaker fsync, checks turned off, a stale or approximate value: if a speedup needs one, stop and report it as a decision with the numbers. **Why:** the person weighs a trade; a worker doesn't make it for them.
- **Push everything else as far as it goes**, in this order: do we need this work at all, can we do less of it, can we do it more efficiently, can we do it elsewhere or later, can we do it in parallel. **Why:** the fastest work is work removed, and it costs nothing in function.
- **Robustness is function too.** Behaviour under failure, overload, restarts and bad input stays at least as sound as before. **Why:** a speedup that adds a way to stall, lose data or crash is a trade.
- **A cache is not the first fix.** Make the uncached path fast first. Keep a cache only when the problem demands it and its management is correct, adaptive and worth its upkeep. **Why:** a cache is a second copy of the truth. It can go stale, and it often hides the real fault.
- **Check every reader before you leave something out.** Show that nothing reads it, from the code, types or specs; don't assume it. **Why:** what looks unused is often read somewhere you didn't look.
- **When a target can't be met with everything intact, report the floor**: the best number reachable with functionality kept, and what limits it. **Why:** an honest floor is a result; a quiet trade is a bug.

You skipped this when a change got faster by returning less, later, staler or less safely, or when such a change was offered as the recommended option.
