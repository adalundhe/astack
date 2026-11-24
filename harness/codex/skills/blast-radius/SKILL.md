---
name: blast-radius
description: "Identify what a change could break outside its diff and verify the core safety assumption by running real code. Use before refactoring or removing shared code, or when reviewing a risky change."
---

# Blast radius

Find what a change could break beyond its diff before it ships.

1. **Read the full behavior change:** what is added, modified, or removed—including subtle behavioral shifts the diff doesn't spell out.
2. **Isolate the core safety assumption.** Most risky-looking changes depend on one key invariant (for example, "this only drops entries that are already dead"). Identify it explicitly so you can test it directly.
3. **Look past grep.** Inspect the pinned source of called libraries; lifecycle edges (startup, shutdown, retries, concurrency); boundary data (APIs, persisted data, wire formats, config, other services or languages); and callers several hops downstream.
4. **Prove the assumption by running real code,** as high on the trust ladder (**prove-it**) as you can reach: run a script, test, or local reproduction against the real system.
5. **Report clearly:** what the change does; the core safety assumption (marked proven or unproven); each concrete risk (how and where it breaks, likelihood, severity); what you checked and cleared; and the cheapest check that would catch real breakage.

Referenced skills: `prove-it` (`../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's blast-radius skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
