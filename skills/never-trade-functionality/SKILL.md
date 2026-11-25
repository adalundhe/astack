---
name: never-trade-functionality
description: "Ensure optimizations preserve exact results, freshness, durability, error visibility, and features. Use when optimizing or proposing approximate/deferred variants."
disable-model-invocation: true
---

# Never trade functionality for speed

A faster implementation must keep the same accuracy, freshness, guarantees, and visible errors, because silent accuracy or freshness drops are regressions, not speedups.

## Start with

1. **Optimize in order** (`clamber`): eliminate unnecessary work, do less work, do it more efficiently, defer off the hot path, or parallelize.
2. **Keep robustness intact:** don't introduce new ways to stall, lose data, or crash.
3. **Speed up the uncached path first** before reaching for a cache (**minimize-state-stores**).
4. **Prove unused work is actually unused** before removing it—never assume.
5. **Research before accepting a trade-off:** run **research-this** first to find designs that hit the target without dropping guarantees. Measure viable candidates (`swarm-hypothesis`, **ab-test**).
6. **Escalate only proven limits:** if **research-this** and measurements prove no compliant design works, report the best compliant result and bottleneck. Only then present the trade-off with numbers (**decisions-in-plain-words**).

## Watch for

- acknowledging writes before durability;
- disabling validation or safety checks;
- stale, approximate, sampled, or truncated outputs;
- silently dropped fields, features, or swallowed errors;
- reduced precision, or deferred work whose delay users observe.

**The test:** does every user still get the same values, freshness, guarantees, and error behavior?

## When it doesn't fit

- removing work proven to have no readers;
- a trade-off proven unavoidable after **research-this** and explicitly approved by the person with numbers;
- an approximation explicitly requested by the spec (e.g. an estimate or progress indicator).

**Showing it:** run old and new implementations on identical inputs—including edge cases and failure modes—and diff what users observe.
