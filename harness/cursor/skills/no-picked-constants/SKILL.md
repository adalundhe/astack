---
name: no-picked-constants
description: "Every limit, size, threshold, timeout, rate or interval the system acts on is learned or derived, never picked. Use when writing, reviewing or proposing such a number."
---

# No picked constants

We do not support arbitrary constants. We support learned and data-derived values.

**Why:** a picked number fits the machine and the load it was picked on, and nothing else.

- Learn values that depend on the machine or the load at runtime, and keep learning as conditions change. A value measured once and frozen is still picked.
- Derive facts from a cited source, such as a protocol field, an OS limit read at runtime, or a specification, and cite it in the code.
- Bound by the resource, not a round number: a queue by the memory it charges, not by 4,096 entries.
- With no data yet, say so and say how to get it. Never fill the gap with a guess, and never offer the person a menu of numbers.
- Settings a person chooses, such as how long to keep history, are the exception. Give them a sensible default the person can change.
