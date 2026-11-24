---
name: check-your-boundaries
description: "Parse outside data into the program's own types once, where it enters, and trust those types inside. Use when writing or reviewing code that reads requests, arguments, config, environment, files, rows or replies, or that adds validation."
---

# Check your boundaries

Parse outside data into the program's own types where it enters, and trust those types inside.

## Start with

1. **Parse at the boundary.** Requests, CLI arguments, config, environment variables, files, database rows and replies from other services each pass through one parse step that returns the program's own type, or a typed error (**no-hidden-flow-control**).
2. **Trust the types inside:** no re-validation, and no defensive null checks on what a type guarantees. If a check seems needed inside, the type is too loose: tighten it.
3. **Give easily swapped values their own types,** such as two kinds of ID or two units sharing a primitive, when mixing them up is a real failure. Check them once, where they're made.
4. **Derive types from the schema that owns the shape** (an API definition, a database schema, a protocol file), rather than a second copy by hand.
5. **Keep logic in plain functions,** free of framework and transport types, behind a thin shell whose types stay out of the core.

## Watch for

- the same validation or null check repeated on data that already crossed a boundary;
- raw outside data (dictionaries, JSON objects, environment strings, request objects, database rows) passed deep into the code;
- framework or transport types in the signatures of core logic;
- hand-written types copying a schema that exists;
- functions taking several values of one primitive type that are easy to swap;
- business logic inside handlers, controllers or framework callbacks.

**The test:** is this data crossing a boundary right now? If not, it shouldn't need checking. If so, this is where it's parsed, once.

## When it doesn't fit

- a check where data enters another trust domain, such as before a write to another system, against that system's contract;
- input checks in a library's public API, which is a boundary for its callers;
- an assertion of an invariant the type system can't express, made once where the value is built;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

**Showing it:** send malformed input through the real entry point and show it getting past the edge.

<!-- Adapts pstack's boundary-discipline and type-system-discipline principles (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
