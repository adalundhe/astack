---
name: blast-radius
description: "Identify what a change can break outside its diff and verify the core safety assumption on real code. Use before refactoring shared code or reviewing a risky change."
---

# Blast radius

Find what a change could break beyond its diff before it ships.

1. **Read the full behavior change:** list everything added, modified, or removed. Include subtle behavioral shifts the diff never spells out.
2. **Name the core safety assumption:** most risky changes rest on one key invariant (for example, "this only drops already-dead entries"). State it explicitly so you can attack it directly.
3. **Look past grep,** because reflection, dynamic dispatch, and external consumers never appear in symbol searches. Inspect every indirect seam:
   - pinned source of called libraries and callers several hops downstream;
   - dynamic, observability, and CI consumers (reflection, plugins, dashboards, alerts, metrics, pipelines, scripts);
   - lifecycle edges: startup, shutdown, retries, and concurrency;
   - live mixed-version rollout and rollback: old pods, CronJobs, migration waves, cross-repo order, and rolled-back releases (**safe-to-deploy**);
   - boundary data: APIs, persisted records, wire formats, config, and other services;
   - repo docs describing changed behavior, interfaces, config, or operations (**technical-writing**).
4. **Prove the assumption on real code:** run a script, test, or local repro as high on **prove-it**'s trust ladder as you can reach.

**Reply:**
- what changed and whether the core safety assumption is proven or unproven;
- each concrete risk (where it breaks, likelihood, severity);
- what held under real execution;
- the cheapest check that catches real breakage.

Referenced skills: `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's blast-radius skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
