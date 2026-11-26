---
name: stepped-complexity
description: "Make each step up in user use case require the exact minimal new interface or API surface needed. Use when designing, expanding, or reviewing user interfaces and contracts."
---

# Stepped complexity

Each step up in user need should require the exact, minimal new contract surface needed to achieve it. Simple cases stay trivial, and advanced cases build smoothly on the tier below.

**How each role uses this principle:**
- **Workers:** guide CLI, TUI, UI, API, and config implementation so every capability scales cleanly by tier.
- **Workers & Researchers:** evaluate how to expand existing interfaces without breaking or bloating simpler tiers (**next-step**).
- **Reviewers:** spot surface bloat and recommend interface reductions during reviews (**rightsize-contracts**).

## Start with

1. **Order real use cases from simplest to most advanced.** Ground each tier in tests, docs, examples, telemetry, and live code before inventing flags or fields.
2. **Keep the base tier effortless.** Provide safe defaults and derive anything already available from existing integrations, code, or environment context.
3. **Add exact minimal surface per step.** Unlock tier $N+1$ by composing one clear concept onto tier $N$. Never force callers to rewrite from scratch or learn unrelated knobs.
4. **Keep contract semantics predictable.** Use clear names, avoid hidden side effects, and keep options orthogonal (**delight-users**, **no-hidden-config**, **no-bolt-ons**).

## Watch for

- CLI commands carrying flag bloat where two clear concepts or inferred defaults cover every tier;
- deeply nested config or API schemas serving wildly different complexity tiers inside one call;
- config options asking users for data the code can derive programmatically from existing integrations or resources;
- overloaded flags or options with counterintuitive side effects or hidden mode switches;
- hidden surface interfaces (undocumented env vars, implicit files, or magic strings);
- cliff jumps where one small step in need requires a completely different interface.

**The test:** what exact new contract surface must a user learn to move from tier $N$ to tier $N+1$? Can any part of it be derived, simplified, or aligned with tier $N$?

## When it doesn't fit

- frozen external wire protocols, schemas, or regulatory specs you cannot alter;
- explicit security, billing, or destructive safety gates that must never be implicit (**least-privilege**, **safe-to-deploy**).

**Showing it:** place two adjacent user tiers side by side and show the excess flags, nested options, redundant config, or overloaded behavior required to step from tier $N$ to tier $N+1$.

Referenced skills: `next-step` (`../next-step/SKILL.md`), `rightsize-contracts` (`../rightsize-contracts/SKILL.md`), `delight-users` (`../delight-users/SKILL.md`), `no-hidden-config` (`../no-hidden-config/SKILL.md`), `no-bolt-ons` (`../no-bolt-ons/SKILL.md`), `least-privilege` (`../least-privilege/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`). Read any cited skill file before acting when its trigger applies.
