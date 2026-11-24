---
name: never-trade-functionality
description: "Ensure optimizations keep exact results, freshness, durability, error visibility, and features—researching compliant approaches before claiming any trade-off is unavoidable. Use when optimizing or proposing approximate/deferred variants."
disable-model-invocation: true
---

# Never trade functionality for speed

A faster implementation must still do everything the slower one did: same accuracy, freshness, guarantees, and visible errors.

## Start with

1. **Optimize in order** (**clamber**): eliminate unnecessary work, do less work, do it more efficiently, defer or move it off the hot path, parallelize it.
2. **Keep robustness intact:** don't introduce new ways to stall, lose data, or crash.
3. **Speed up the uncached path first** before reaching for a cache (**minimize-state-stores**).
4. **Prove unused work is actually unused** before removing it—never assume.
5. **Research before accepting a trade-off:** if you seem unable to hit the target without dropping functionality or guarantees, run **research-this** first to find how other systems, algorithms, or architectures achieve the goal *without* compromising, and test viable candidates (**explore-the-limits**, **ab-test**).
6. **Escalate only proven limits:** if **research-this** and measurement confirm no compliant design can hit the target, report the best compliant result, the concrete bottleneck or fundamental limit, what you researched and tested, and only then present the trade-off with numbers to the person (**decisions-in-plain-words**).

## Watch for

Acknowledging writes before durability; disabling validation or checks; stale, approximate, sampled, or truncated outputs; silently dropped fields or features; swallowed errors; reduced precision; or deferred work whose delay users observe.

**The test:** does every user still get the same values, freshness, guarantees, and error behavior?

## When it doesn't fit

- removing work proven to have no readers;
- a trade-off proven unavoidable after **research-this** and explicitly approved by the person with numbers;
- an approximation explicitly requested by the spec (e.g. an estimate or progress indicator).

**Showing it:** run old and new implementations on identical inputs—including edge cases and failure modes—and diff what users observe.
