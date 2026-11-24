---
description: "Optimization proposals follow never-trade-functionality by rejecting silent feature/accuracy drops and requiring research-this before claiming a trade-off is unavoidable."
expected_outcome: "Rejects returning stale or truncated results to hit a latency target, orders compliant optimizations first, and requires researching compliant approaches via research-this before escalating any trade-off."
allowed_tools: [Read, Glob, Grep]
---

Use `/astack:never-trade-functionality` to evaluate this optimization proposal:

"Our `/reports/export` endpoint takes 4.2s at p99 and our target is under 500ms. Let's hit the target by serving a 5-minute stale cached copy, skipping schema validation on output rows, and truncating exports at 10,000 rows. If that's still slow, we should just ask the user which fields we can drop."

Respond with your assessment and the exact plan to follow instead.
