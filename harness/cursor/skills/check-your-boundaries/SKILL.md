---
name: check-your-boundaries
description: "Parse and validate external data into domain types once at the boundary, then trust those types inside. Use when writing or reviewing code handling requests, CLI args, config, env vars, files, DB rows, or API replies."
disable-model-invocation: true
---

# Check your boundaries

Parse external data into the program's own types once where it enters, then trust those types inside.

## Start with

1. **Parse at the edge.** Run requests, CLI arguments, config, environment variables, files, database rows, and external API replies through one parse step that returns a domain type or a typed error (**no-hidden-flow-control**).
2. **Trust types inside.** Don't repeat validation or add defensive null checks for guarantees the type already enforces. If internal code feels like it needs a check, tighten the type.
3. **Distinguish swappable primitives.** Wrap values that share a primitive type (such as two kinds of IDs or different units) in distinct types when mixing them up causes real bugs, and validate once at construction.
4. **Derive types from the source schema.** Generate or derive types from the owning schema (API spec, database schema, protocol definition) instead of maintaining a hand-written copy.
5. **Keep core logic pure.** Keep framework and transport types in a thin outer shell so core logic operates on plain domain types and functions.

## Watch for

- repeated validation or null checks on data that already crossed a boundary;
- raw external payloads (dicts, JSON blobs, env strings, HTTP request objects, DB rows) passed deep into core logic;
- framework or transport types appearing in core function signatures;
- hand-written types duplicating an existing schema;
- functions accepting multiple easily swapped parameters of the same primitive type;
- business logic embedded in route handlers, controllers, or framework callbacks.

**The test:** is this data crossing a boundary right now? If yes, parse it once here. If not, the code shouldn't need to re-validate it.

## When it doesn't fit

- validating data leaving your system for another trust domain against that system's contract;
- input validation on a library's public API (which is a boundary for its callers);
- a single construction-time assertion for an invariant the type system can't express;
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** send malformed input through the real entry point and show it getting past the boundary.

<!-- Adapts pstack's boundary-discipline and type-system-discipline principles (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
