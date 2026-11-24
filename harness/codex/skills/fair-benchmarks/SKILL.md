---
name: fair-benchmarks
description: "Keep cross-system benchmarks fair: identical client, platform, and concurrency, release/production tuning on all sides, error checking, and alternating runs. Use before running or trusting competitor benchmarks."
disable-model-invocation: true
---

# Fair benchmarks

Compare systems on an equal footing: same platform, same load driver, and production tuning on every side.

- **Same load driver:** one client for every system with identical concurrency, batching, pacing, and timeouts (each system may use its native protocol inside the driver).
- **Same hardware and OS:** same machine, disk, and filesystem; either containerize all systems or none.
- **Shipped production tuning:** release builds and documented production settings for every side. Leaving a competitor on debug or unconfigured defaults invalidates the comparison.
- **Verify responses and count errors:** refused or corrupted responses are often the fastest.
- **Control noise:** alternate runs round by round, repeat until noise is characterized, log host load, and discard runs affected by external load.
- **Record full reproducibility details:** driver, hardware, versions, configs, and exact commands alongside the numbers.

<!-- Adapts pstack's benchmark-checklist skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
