---
name: no-picked-constants
description: "Avoid hardcoded limits, timeouts, batch sizes, or thresholds; derive from specs or adapt at runtime. Use when writing, reviewing, or proposing behavioral constants."
disable-model-invocation: true
---

# No picked constants

Don't hardcode arbitrary behavioral constants. Learn load-dependent values at runtime or derive fixed limits from a cited source.

## Start with

1. **Adapt machine- or load-dependent values at runtime** as conditions change. Measuring once and freezing a magic number still fails, because hardware and load drift.
2. **Derive fixed limits from a cited source** (protocol spec, OS/hardware limit, RFC) and cite it in code.
3. **Bound by the actual resource, not an arbitrary count,** because entry sizes vary wildly. For example, cap a queue by memory bytes rather than `4096` entries.
4. **If you lack data, say so** and state how to measure it. Never guess a number or offer an arbitrary menu.

## Watch for

Behavior-driving numbers: limits, buffer/pool sizes, timeouts, retries, backoff multipliers, rates, intervals, and percentages. Suspicious tells include round numbers, arbitrary powers of two, copied constants, and undocumented defaults.

**The test:** where did this number come from? Will it still hold on different hardware, heavier load, or larger inputs?

## When it doesn't fit

- user-configurable settings (e.g. retention period) with a sensible documented default (**no-hidden-config**);
- constants derived from a cited external source;
- mathematical/physical constants and unit conversions;
- deterministic test inputs and seeds.

**Showing it:** run the code where the picked constant breaks down—different hardware, heavier load, or larger inputs (**benchmarking**).

Referenced skills: `no-hidden-config` (`../no-hidden-config/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`). Read any cited skill file before acting when its trigger applies.
