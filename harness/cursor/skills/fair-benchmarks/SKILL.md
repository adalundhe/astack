---
name: fair-benchmarks
description: "Compare against other systems fairly: same client, same platform, every side tuned as it ships. Use before running, reporting or trusting any benchmark against a competitor or another implementation."
---

# Fair benchmarks

Compare against other systems fairly: the same platform and the same client for every system.

- One driver for every system, with the same concurrency, batching, pacing and timeouts. Each system may speak its own protocol inside it.
- Same machine, OS, disk and filesystem. Containers for all or for none.
- Tune every side as it ships: release builds, production settings. A side left on defaults loses to its configuration.
- Count errors and check answers. Refused or wrong requests are often the fastest.
- Alternate the runs, repeat until you know the noise, record the machine's load, and discard runs made under someone else's load.
- Record the client, platform, versions, settings and command with the numbers. Without them, no one can check the result.

<!-- Adapts pstack's benchmark-checklist skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
