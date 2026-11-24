---
description: "Proposing queue bounds and retry timeouts follows no-picked-constants instead of inventing arbitrary magic numbers."
expected_outcome: "Refuses to pick arbitrary magic numbers (like 4096 entries or 30s timeout), instead bounding by actual resources, deriving from cited specs/OS limits, adapting at runtime, or stating how to measure."
allowed_tools: [Read, Glob, Grep]
---

Use `/astack:no-picked-constants` to answer:

We're adding an in-memory ingestion queue and an upstream HTTP retry loop to our service. What queue length limit, batch size, and retry timeout constants should we hardcode?
