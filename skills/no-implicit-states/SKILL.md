---
name: no-implicit-states
description: "Make state machines explicit: named states in one type, transitions in one place, every state handled. Use when writing or reviewing code whose behaviour depends on what happened before."
---

# No implicit states

Make state machines explicit: named states, held in one type, changed in one place.

## Start with

1. **Name the states in one type:** an enum, tagged union or sum type, by the language's own means. Data that exists only in some states lives inside them, so impossible combinations can't be written.
2. **Put transitions in one place:** a function or table from state and event to the next state, handling or rejecting every event in every state.
3. **Handle every state,** checked by the compiler or a linter, with no default branch to silently absorb a new one.
4. **Test each transition,** each rejected event, and the paths users rely on.
5. **Chart it beside the code** when others depend on it: a protocol, a product flow, an integration (**show-the-states**).

## Watch for

- booleans or nullable fields that together mean a phase: `isLoading`, `error`, `data`; `connected`, `retrying`;
- fields valid only in some phases: a token empty until sign-in, a timestamp whose presence means done;
- a status string or number compared in scattered places;
- calls that must happen in order (open, start, stop) with nothing enforcing it;
- flags flipped in callbacks, handlers or retries, and counters that decide behaviour;
- branches marked "can't happen".

**The test:** is any combination of these values invalid, or does their order matter? Then it's a state machine.

## When it doesn't fit

- values that are truly independent: every combination is valid, in any order;
- a local flag inside one short function, where the whole flow is visible at once;
- state a library or framework already models explicitly, used as it intends;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

**Showing it:** a test that drives the code into a combination it shouldn't allow, such as loading and failed at once.

<!-- Adapts pstack's type-system-discipline principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
