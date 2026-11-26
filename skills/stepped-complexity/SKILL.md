---
name: stepped-complexity
description: "Make each step up in user use case require only the minimal new interface or API surface needed. Use when designing, expanding, or reviewing user interfaces and contracts."
disable-model-invocation: true
---

# Stepped complexity

Each step up in user need should require only the minimal new contract surface needed to achieve it. Simple cases stay trivial, and advanced cases extend the tier below without replacing it.

**How each role uses this principle:**
- **Workers:** guide CLI, TUI, UI, API, and config design so each tier adds only the parameters it uses.
- **Workers & Researchers:** evaluate interface expansions without breaking or bloating simpler tiers (**next-step**).
- **Reviewers:** spot surface bloat and recommend interface reductions during reviews (**rightsize-contracts**).

## Start with

1. **Order real use cases from simplest to most advanced.** Ground each tier in tests, docs, examples, telemetry, and live code before inventing flags or fields.
2. **Keep the base tier zero-config where possible.** Provide safe defaults and derive values already available from existing integrations, code, or environment context.
3. **Add minimal surface per step.** Unlock tier $N+1$ by composing one clear concept onto tier $N$. Never force callers to rewrite from scratch or learn unrelated knobs.
4. **Keep contract semantics predictable.** Use consistent names, avoid hidden side effects, and keep options orthogonal (**delight-users**, **no-hidden-config**, **no-bolt-ons**).

## Watch for

- CLI commands carrying flag bloat where two clear concepts or inferred defaults cover every tier;
- deeply nested config or API schemas serving distinct complexity tiers inside one call;
- config options asking users for data the code can derive programmatically from existing integrations or resources;
- overloaded flags or options with counterintuitive side effects or hidden mode switches;
- hidden surface interfaces (undocumented env vars, implicit files, or magic strings);
- cliff jumps where one small step in need requires a completely different interface.

**The test:** what new contract surface must a user learn to move from tier $N$ to tier $N+1$? Can any part of it be derived, simplified, or aligned with tier $N$?

## When it doesn't fit

- frozen external wire protocols, schemas, or regulatory specs you cannot alter;
- explicit security, billing, or destructive safety gates that must never be implicit (**least-privilege**, **safe-to-deploy**).

**Showing it:** place two adjacent user tiers side by side and show the excess flags, nested options, redundant config, or overloaded behavior required to step from tier $N$ to tier $N+1$.
