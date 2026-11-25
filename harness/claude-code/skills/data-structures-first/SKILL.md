---
name: data-structures-first
description: "Design data representations, invariants, ownership, and access patterns before writing control flow. Use when designing features, schemas, core modules, or refactors."
disable-model-invocation: true
---

# Data structures first

Get the data representation right before writing control flow. Clear data structures make algorithms short and obvious, because the right shape eliminates defensive branches and synchronization glue.

## Start with

1. **List access patterns and invariants first:** note what is read, written, queried, ordered, or joined, at what scale, and what must stay true.
2. **Make invariants hold by construction:** choose types, keys, enums, and ownership so illegal states cannot be represented (**no-implicit-states**).
3. **Match representations to access patterns:** weigh maps vs. slices, flat structs vs. pointer graphs, and append logs vs. mutable tables. Verify non-obvious layouts with **ab-test**.
4. **Sketch concrete records first:** write exact types with 2–3 realistic instances (including edge cases). Trace main operations by hand before coding.
5. **Keep one canonical representation:** derive views instead of maintaining parallel arrays, shadow maps, or duplicated fields (**minimize-state-stores**).

## Watch for

- parallel arrays or maps indexed by the same position or key that must stay manually synchronized;
- stringly-typed dicts, untyped JSON blobs, or bags of optional fields standing in for real domain types;
- complex nested conditionals compensating for an awkward representation;
- repeated translation layers converting the same data back and forth between slightly different shapes;
- pointer-chasing or excessive heap allocations on hot paths when a contiguous structure fits naturally.

**The test:** if you show someone only the data types and sample values, can they predict how the algorithms work?

## When it doesn't fit

- thin glue constrained by an external wire format or schema (parse into clean domain types at the boundary);
- throwaway prototypes (`play-with-me`);
- an alternative layout backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** contrast the branching, synchronization code, or allocations required by the current shape against a cleaner representation on the same operations.

Referenced skills: `no-implicit-states` (`${CLAUDE_SKILL_DIR}/../no-implicit-states/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `minimize-state-stores` (`${CLAUDE_SKILL_DIR}/../minimize-state-stores/SKILL.md`). Read any cited skill file before acting when its trigger applies.
