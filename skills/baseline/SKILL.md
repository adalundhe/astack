---
name: baseline
description: "Keep cross-system benchmarks and baselines fair: identical client, platform, and concurrency, production tuning on all sides, verified work, error checking, and alternating runs. Use before running or trusting competitor benchmarks."
disable-model-invocation: true
---

# Baseline

Compare systems on an equal footing. One untuned default or mismatched client invalidates the entire measurement.

- **Same load driver:** use one client for every system with identical concurrency, batching, pacing, and timeouts. Each system may use its native protocol inside the driver.
- **Same hardware and OS:** run on the same machine, disk, and filesystem. Either containerize every system or none.
- **Production tuning on every side:** use release builds and documented production configs. Treat any side held back by a conservative default, tiny pool cap, or debug flag as **untuned**, and fix it before trusting the numbers.
- **Confirm real work and count errors:** consume outputs and check status codes, because lazy evaluation or silent rejections can masquerade as high throughput.
- **Control and report variance:** alternate runs round by round, log host load, and discard noisy runs. Size $n$ for your target effect (location MDE, spread ratio $r = \sigma_{\text{new}}/\sigma_{\text{base}}$, or within-run $\text{p99}-\text{p50}$ over $\ge 10/q$ requests). Report median + 95% CI, $\sigma$ (Brown–Forsythe or BCa $\log\sigma$-ratio CI), and $\text{p99}-\text{p50}$.
- **Record reproducibility details:** save driver, hardware, versions, configs, and exact commands beside the numbers.

<!-- Adapts pstack's benchmark-checklist skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
