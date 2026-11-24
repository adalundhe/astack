---
description: "In Go mode, a request for hardcoded queue/batch/timeout numbers routes to no-picked-constants and refuses to invent arbitrary constants."
expected_outcome: "Reads no-picked-constants/SKILL.md, refuses to invent arbitrary numbers, bounds queues by resource usage, derives/adapts limits at runtime, and explains what to measure."
allowed_tools: [Read, Glob, Grep]
---

`/astack:go` We're adding an in-memory ingestion queue and an upstream HTTP retry loop to our service. What queue length limit, batch size, and retry timeout values should we put in the code?
