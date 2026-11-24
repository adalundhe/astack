---
name: no-implicit-states
description: "Model state machines explicitly with named states in one type, centralized transitions, and exhaustive handling. Use when writing or reviewing code whose behavior depends on prior state."
disable-model-invocation: true
---

# No implicit states

Make state machines explicit: named states in one type, transitions in one place, and exhaustive handling everywhere.

## Start with

1. **Represent states in one type:** an enum, tagged union, or sum type idiomatic to the language. Store state-specific data inside its variant so invalid combinations are unrepresentable.
2. **Centralize transitions:** route `(state, event) -> next_state` through a single function or transition table that explicitly handles or rejects every event in every state.
3. **Enforce exhaustive handling** via compiler or linter checks—avoid wildcard default branches that silently absorb newly added states.
4. **Test transitions directly:** cover valid transitions, rejected events, and critical user paths.
5. **Diagram shared state machines** alongside the code for protocols, user flows, or integrations (**show-the-states**).

## Watch for

- groups of booleans or nullable fields encoding a lifecycle (`isLoading` + `error` + `data`; `connected` + `retrying`);
- fields valid only in certain phases (e.g. a token empty until login, or a nullable timestamp meaning "completed");
- raw status strings or numeric codes compared across scattered files;
- ordering requirements (`open`, `start`, `stop`) enforced only by convention;
- flags flipped across callbacks/retries, or counters implicitly driving mode switches;
- branches commented `"can't happen"`.

**The test:** is any combination of these fields invalid, or does call order matter? If so, model it as an explicit state machine.

## When it doesn't fit

- genuinely independent flags where every combination is valid in any order;
- a local flag scoped inside one short function whose entire flow is visible at a glance;
- state already modeled explicitly by a framework or library, used as intended;
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** write a test that drives the code into an illegal combination (e.g. both loading and failed at the same time).

Referenced skills: `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's type-system-discipline principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
