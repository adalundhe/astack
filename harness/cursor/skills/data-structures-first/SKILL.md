---
name: data-structures-first
description: "Design data representations, invariants, ownership, and access patterns before writing algorithms or control flow. Use when designing new features, schemas, core modules, or refactoring tangled logic."
disable-model-invocation: true
---

# Data structures first

Get the data representation right before writing control flow. Clear data structures make algorithms short and obvious; the wrong representation forces complex, buggy code around it.

## Start with

1. **List the real access patterns and invariants first:** what gets read, written, queried, ordered, or joined; at what frequency and scale; and what must always hold true.
2. **Make invariants hold by construction:** choose types, keys, enums, and ownership boundaries so illegal states and mismatched units can't be represented (**no-implicit-states**, **check-your-boundaries**).
3. **Pick representations for actual access patterns:** index/map vs. contiguous slice/array, flat struct-of-arrays vs. pointer-heavy graphs, append-only log vs. mutable table. Verify non-obvious layout choices with **benchmarking** or **ab-test**.
4. **Sketch concrete records before code:** write out the exact types/schemas with 2–3 realistic sample instances (including edge cases) and trace the main operations by hand before implementing functions.
5. **Keep one canonical representation:** derive views instead of maintaining parallel arrays, shadow maps, or duplicated fields (**minimize-state-stores**).

## Watch for

- parallel arrays/maps indexed by the same position or key that must stay manually synchronized;
- stringly-typed dicts, untyped JSON blobs, or bags of optional fields standing in for real domain types;
- complex nested conditionals compensating for an awkward representation;
- repeated translation/adapter layers converting the same data back and forth between slightly different shapes;
- pointer-chasing or excessive heap allocations on hot paths when a contiguous structure fits naturally.

**The test:** if you show someone only the data types and sample values, can they predict how the algorithms work?

## When it doesn't fit

- thin glue code strictly constrained by an external wire format or third-party schema (parse into clean internal types at the boundary if core logic touches it);
- throwaway prototypes (**play-with-me**);
- an alternative layout backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** contrast the branching, synchronization code, or allocations required by the current shape against a cleaner representation on the same operations.

Referenced skills: `no-implicit-states` (`../no-implicit-states/SKILL.md`), `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `minimize-state-stores` (`../minimize-state-stores/SKILL.md`), `play-with-me` (`../play-with-me/SKILL.md`). Read any cited skill file before acting when its trigger applies.
