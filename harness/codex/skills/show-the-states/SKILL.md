---
name: show-the-states
description: "Draw how a system moves between states: what triggers each transition, how likely it is when there's data, and the path any failure took. Use to debug, to understand or research a system, to plan work, and to show a design, review or verification result."
---

# Show the states

Draw how a system moves between states, so the reader sees what happens, when, and how it fails.

1. **Context first:** the system, the question the chart answers (how this failed, how this works, what we'll build, whether this is right), its scope, and the source of each state and transition: code (file and line), a model, logs and traces, or the design.
2. **Use the reader's words.** A state is what users or operators see or care about ("Paying", "Lease held, write pending"), not a variable name. A transition says what happens and what triggers it: an action ("you press play"), an event ("the payment clears"), a timer ("the lease expires"), a failure ("the connect fails"). A condition goes in brackets: "you press play [while the file loads]".
3. **Show the structure:** start and end states, nested states for phases, parallel regions for parts that change independently.
4. **Give probabilities** when asked, or when data exists: each transition's probability or rate, and its source (events counted in logs or metrics, with the period and count). Asked with no data: simulate, running the model or the code on recorded or researched inputs, seeded, with enough runs to report a spread; or **research** published rates. Never guess (**no-picked-constants**).
5. **Mark what goes wrong:** each state that breaks a rule, with the rule, and each failure as the shortest path to it. When debugging, draw the path the failure actually took, each step with its evidence (a log line, a span, a test step), and mark the transition that shouldn't exist, or the one that was missing (**bugs-by-scenario**).
6. **Readable at a glance:** merge states that behave alike and drop steps the reader doesn't need, but don't merge states that break different rules, hide a step of a failure path, or strand a state. Say what you left out.
7. **Mermaid** (`stateDiagram-v2`), so it renders where the reader is, kept with its context in the report, review, brief or architecture decision it serves.

In planning, mark which task builds which states and transitions. The chart goes in the briefs, and review checks the code against it.

<!-- Adapts pstack's statechart skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
