---
name: show-the-states
description: "Diagram a system's states, triggers, conditions, failure paths, and observed probabilities in Mermaid stateDiagram-v2. Use for debugging, onboarding, design, planning, or reviews."
---

# Show the states

Diagram how a system moves between states so readers can immediately see what happens, what triggers it, and how failures unfold.

1. **State the context first:** the system, the question the chart answers (how it failed, how it works, what we're building, whether it's correct), its scope, and where states/transitions come from (code `file:line`, formal model, logs/traces, or design).
2. **Use domain words, not variable names.** Name states after what users or operators care about (`"Paying"`, `"Lease held, write pending"`). Label transitions with the action, event, timer, or failure (`"user clicks play"`, `"payment clears"`, `"lease expires"`, `"connect fails"`), putting guard conditions in brackets (`"user clicks play [while file loads]"`).
3. **Include structure:** start/end states, nested substates for phases, and parallel regions for independent components.
4. **Add probabilities when asked or when data exists:** show transition rates/probabilities with their source (counted log/metric events, sample window, and count). If asked without data, run a seeded simulation on recorded or researched inputs with enough runs to report spread, or use **research-this** for published rates—never guess (**no-picked-constants**).
5. **Highlight failures:** mark invariant-violating states (naming the broken rule) and shortest paths to each failure. When debugging, trace the actual failure path with evidence per step (log line, trace span, test step) and flag the unwanted or missing transition (**bugs-by-scenario**).
6. **Keep it scannable:** collapse equivalent states and omit irrelevant steps, without merging distinct rule violations, hiding failure steps, or stranding states. Note what you omitted.
7. **Render in Mermaid** (`stateDiagram-v2`) inline alongside its context in the report, review, brief, or AD.

During planning, annotate which task builds which states and transitions; include the diagram in briefs and check code against it during review.

Referenced skills: `research-this` (`../research-this/SKILL.md`), `no-picked-constants` (`../no-picked-constants/SKILL.md`), `bugs-by-scenario` (`../bugs-by-scenario/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's statechart skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
