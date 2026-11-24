---
name: fair-benchmarks
description: "Keep cross-system benchmarks fair: identical client, platform, and concurrency, release/production tuning on all sides (no untuned caps), verified real work, error checking, and alternating runs. Use before running or trusting competitor benchmarks."
disable-model-invocation: true
---

# Fair benchmarks

Compare systems on an equal footing: same platform, same load driver, verified work, and production tuning on every side.

- **Same load driver:** one client for every system with identical concurrency, batching, pacing, and timeouts (each system may use its native protocol inside the driver).
- **Same hardware and OS:** same machine, disk, and filesystem; either containerize all systems or none.
- **Shipped production tuning (no untuned ceilings):** use release builds and documented production settings on every side. Treat any side held back by a conservative default, small pool/cache/buffer cap, or debug flag as **untuned**—fix the config before trusting or publishing the comparison.
- **Confirm the work ran and count errors:** verify/consume outputs so lazy evaluation, JIT dead-code elimination, or refused/corrupted responses can't masquerade as fast throughput.
- **Control and report variance:** alternate runs round by round, size $n$ for the metric under test (broad dispersion requires more runs than a location shift; rare tails require enough requests per run to compute each run's own $\text{p99}-\text{p50}$ and compare those across runs), log host load, discard runs affected by external load, and report location (median + 95% CI), broad spread ($\sigma$ + Brown–Forsythe or BCa/studentized $\log\sigma$-ratio CI), and within-run tail spread ($\text{p99}-\text{p50}$).
- **Record full reproducibility details:** driver, hardware, versions, configs, and exact commands alongside the numbers.

<!-- Adapts pstack's benchmark-checklist skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
