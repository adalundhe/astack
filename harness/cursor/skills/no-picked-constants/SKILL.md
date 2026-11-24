---
name: no-picked-constants
description: "Avoid hardcoded arbitrary limits, timeouts, batch sizes, or thresholds; derive them from cited specs/OS limits or adapt them at runtime. Use when writing, reviewing, or proposing behavioral constants."
disable-model-invocation: true
---

# No picked constants

Don't hardcode arbitrary behavioral constants. Learn load-dependent values at runtime or derive fixed limits from a cited source.

## Start with

1. **Adapt machine- or load-dependent values at runtime** as conditions change. Measuring once and freezing a magic number is still a picked constant.
2. **Derive fixed limits from a cited source** (protocol spec, runtime OS/hardware limit, RFC) and cite that source in code.
3. **Bound by the actual resource, not an arbitrary count:** e.g. cap a queue by memory bytes rather than `4096` entries.
4. **If you lack data, say so** and state how to measure it—don't guess a number or offer an arbitrary menu of numbers.

## Watch for

Behavior-driving numbers: limits, buffer/batch/pool sizes, thresholds, timeouts, retry counts, backoff multipliers, rates, intervals, percentages. Suspicious tells: round numbers, arbitrary powers of two, identical constants copied across files, and undocumented defaults.

**The test:** where did this number come from, and will it still hold on different hardware, heavier load, or larger inputs?

## When it doesn't fit

- user-configurable settings (e.g. retention period) with a sensible documented default (**no-hidden-config**);
- constants derived from a cited external source;
- mathematical/physical constants and unit conversions;
- deterministic test inputs and seeds.

**Showing it:** run the code where the picked constant breaks down—different hardware, heavier load, or larger inputs (**benchmarking**).
