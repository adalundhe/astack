---
name: blast-radius
description: "Identify what a change could break outside its diff and verify the core safety assumption by running real code. Use before refactoring or removing shared code, or when reviewing a risky change."
---

# Blast radius

Find what a change could break beyond its diff before it ships.

1. **Read the full behavior change:** list everything added, modified, or removed—including subtle behavioral shifts the diff never spells out.
2. **Name the core safety assumption:** most risky changes rest on one key invariant (for example, "this only drops already-dead entries"). State it explicitly so you can attack it directly.
3. **Look past grep.** Inspect every indirect seam:
   - pinned source of called libraries and callers several hops downstream;
   - lifecycle edges: startup, shutdown, retries, and concurrency;
   - live mixed-version rollout and rollback: old pods, CronJobs, migration waves, cross-repo order, and rolled-back releases (**safe-to-deploy**);
   - boundary data: APIs, persisted records, wire formats, config, and other services;
   - repo docs describing changed behavior, interfaces, config, or operations (**technical-writing**).
4. **Prove the assumption on real code:** run a script, test, or local repro as high on the trust ladder (**prove-it**) as you can reach.
5. **Report clearly:** state what changed, whether the core assumption is proven or unproven, each concrete risk (where it breaks, likelihood, severity), what held, and the cheapest check that catches real breakage.

Referenced skills: `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's blast-radius skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
