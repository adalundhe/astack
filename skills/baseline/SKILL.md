---
name: baseline
description: "Keep cross-system benchmarks fair with identical clients, hardware, production tuning, and alternating runs. Use before running or trusting competitor benchmarks."
disable-model-invocation: true
---

# Baseline

Compare systems on an equal footing. One untuned default or mismatched client invalidates the entire measurement.

- **Same load driver:** use one client for every system with identical concurrency, batching, pacing, and timeouts, because client overhead and framing differences distort throughput. Each system may use its native protocol inside the driver.
- **Same hardware and OS:** run on the same machine, disk, and filesystem. Either containerize every system or none, because mismatched hardware or container layers introduce hidden drift.
- **Production tuning on every side:** use release builds and documented production configs. Treat any side held back by a conservative default, tiny pool cap, or debug flag as **untuned**. Fix untuned configs before trusting the numbers.
- **Confirm real work and count errors:** consume outputs and check status codes, because lazy evaluation or silent rejections can masquerade as high throughput.
- **Control and report variance:** alternate runs round by round, log host load, and discard noisy runs. Follow **benchmarking** for run counts, statistical tests, and median/variance reporting.
- **Record reproducibility details:** save driver, hardware, versions, configs, and exact commands beside the numbers.

**Done when:** all sides ran alternating rounds on identical hardware and drivers with verified outputs, documented configs, and **benchmarking** stats.

<!-- Adapts pstack's benchmark-checklist skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
