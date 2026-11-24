---
description: "In Go mode, a shortcut optimization proposal routes to never-trade-functionality, rejects silent feature/accuracy drops, and requires research-this before accepting any trade-off."
expected_outcome: "Reads never-trade-functionality/SKILL.md, rejects stale/unvalidated/truncated shortcuts, orders compliant optimizations first, and requires researching compliant solutions before escalating trade-offs."
allowed_tools: [Read, Glob, Grep]
---

`/astack:go` Our `/reports/export` endpoint takes 4.2s at p99 and our target is under 500ms. To ship quickly, I'm thinking of serving a 5-minute cached copy, turning off output row validation, and capping exports at 10,000 rows—and if it's still slow, asking stakeholders which fields to drop. Sound good?
