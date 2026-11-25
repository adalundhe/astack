# Architecture Decision Format (`AD_<N>.md`)

Store architecture decisions cross-OS at `~/.astack/<project>/architecture/AD_<N>.md` (`$HOME/.astack/<project>/architecture/AD_<N>.md` on POSIX, `%USERPROFILE%\.astack\<project>\architecture\AD_<N>.md` on Windows, honoring `ASTACK_HOME`). Resolve and create the path with `astack-tools arch path <project> --next --ensure`. Published numbers never change.

Create `architecture/` lazily when the first qualifying decision is written.

## Qualification gate

Write an `AD_<N>.md` only when all three hold:

1. **Hard to reverse:** meaningful cost to change later.
2. **Non-obvious without context:** a future reader would ask why it works this way.
3. **Real trade-off:** credible alternatives existed and lost for concrete reasons.

## Template

```md
---
ad_number: <N>
name: <Name>
description: <One sentence: what is decided.>
---

# AD-<N>: <Name>

## Status

Accepted (<YYYY-MM-DD>). <Built (<YYYY-MM-DD>), once built.>

**Related:** AD-<k> (<how it relates>).

## Context

<Current problem walked through one concrete scenario, with code paths and numbers.>

## Decision

<Concrete mechanisms (data structures, protocols, locks, messages), diagrams, and an implementation sketch per settled branch.>

## Non-goals

<What this decision deliberately leaves out.>

## Costs accepted

<Each cost accepted from the ledger (latency, consistency, operational burden), with numbers.>

## Alternatives considered

<Each rejected option: where it diverges, what it costs, and why it lost. Record user overrules as their decision and reasoning.>

## Acceptance criteria

<Checkable bounds, behavior under named conditions, and invariants.>

## Tests

<Each test case and the failure it catches.>

## Evidence

<Citations, benchmarks, A/B write-ups, and production numbers with locations.>
```

## As-built upkeep

After implementation, update `## Status` to `Built (<YYYY-MM-DD>)` (or add a dated `## Status (<YYYY-MM-DD>)` / `> **As built (<YYYY-MM-DD>):**` addendum) recording built modules, deviations, and verifying checks.
