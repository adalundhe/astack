---
name: no-picked-constants
description: "Every limit, size, threshold, timeout, rate or interval the system acts on is learned or derived, never picked. Use when writing, reviewing or proposing such a number."
---

# No picked constants

We don't use arbitrary constants. Values are learned at runtime or derived from a cited source.

## Start with

1. **Learn values that depend on the machine or the load** at runtime, and keep learning as conditions change. A value measured once and frozen is still picked.
2. **Derive facts from a cited source,** such as a protocol field, an OS limit read at runtime or a specification, and cite it in the code.
3. **Bound by the resource, not a round number:** a queue by the memory it uses, not by 4,096 entries.
4. **With no data yet, say so,** and say how to get it. Never fill the gap with a guess, and never offer the person a menu of numbers.

## Watch for

Numbers that decide behaviour: limits, sizes, batch and pool sizes, thresholds, timeouts, retry counts, backoff, rates, intervals, percentages. Round numbers and powers of two are the usual tell, as are the same number repeated in several places and defaults with no source.

**The test:** where did this number come from, and would it still be right on another machine, under another load, at another size?

## When it doesn't fit

- a setting the person chooses, such as how long to keep history, with a sensible, documented default they can change (**no-hidden-config**);
- a fact derived from a cited source, cited in the code;
- mathematical and physical constants, and unit conversions;
- a test's inputs and seeds.

**Showing it:** run it where the number stops fitting: another machine, a heavier load, a larger input (**benchmarking**).
