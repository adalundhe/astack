---
name: prove-it
description: "Verify claims on the real artifact with deterministic repros, measured frequency, and runnable proof. Use before calling work done or reporting/challenging any claim."
disable-model-invocation: true
---

# Prove it

Verify claims on the real system with deterministic reproduction and measured telemetry frequency. Back every claim with the strongest evidence available, and give the person a runnable proof.

## Verify the real thing

Check the actual artifact: run the feature, inspect real output, and read the actual diff. Proxies prove nothing—timestamps, agent summaries, cached output, or "it compiles" are not proof. When a check fails unexpectedly or passes too easily, audit the check itself first. Script checks so anyone can rerun them, and keep outputs accessible.

Classify every verification as **verified**, **not verified**, or **inconclusive**. Never treat inconclusive as a pass, and report negative results openly.

## Deterministic reproduction & empirical frequency

- **Deterministic reproduction:** prove behavior with a repeatable repro using fixed inputs, explicit seeds, and controlled schedules. It must fail before the change and pass after; one lucky run proves nothing.
- **Empirical frequency (`no-picked-constants`):** measure occurrence rates from accessible logs, traces, telemetry, metrics, or usage analytics. Cite source, time window, and sample count; never guess "rare" or "common". If telemetry is unavailable, mark frequency unmeasured and prove behavior deterministically.
- **Intermittent faults:** eliminate nondeterminism structurally via seeded schedulers, pinned clocks, or fault injection (`find-it`). Otherwise compute required clean runs from the conservative 95% lower confidence bound $p_{\text{low}}$ on observed failure rate $k/m$ (not raw $k/m$): $n \ge \lceil \ln(\alpha)/\ln(1-p_{\text{low}}) \rceil$ (and use $\alpha/K$ across $K$ bisect steps; e.g., $3/20$ has $p_{\text{low}} \approx 0.032$, needing $\sim 93$ clean runs at $\alpha=0.05$, not $19$).

## The trust ladder

From weakest to strongest evidence, monotonically aligned with **research-this** source trust weights:

1. Your own (or another agent's) reasoning or memory (unverified).
2. Unverified code you just wrote, or results backed only by mocks, proxies, or informal docs/notes (`0.65–0.70` in `research-this`).
3. Observed internal data, logs, traces, or metrics (`0.80`), plus product docs and peer-reviewed papers (`0.85`).
4. Verified existing source code read without running, or authoritative standards and specifications (`0.90`).
5. Running and measuring the real system: end-to-end tests, live repros, benchmarks, and A/B comparisons (`0.95`).

Push every claim as high up the ladder as practical and state its rung. Challenge weak claims by naming their rung and bringing higher-rung evidence.

## Show your work

Don't assume the person shares your context. Present findings in order:

1. **Problem:** brief restatement of what you investigated.
2. **Hypothesis or solution:** what you tested or built, concisely.
3. **Method & conditions:** steps, exact reproduction environment, and measured frequency (source, window, sample count) when relevant.
4. **Evidence:** raw data, outputs, profiles, traces, telemetry, or benchmarks.

Include a deterministic command, script, minimal repro, or demo the person can run—for failures and successes alike.

**Done when:** every claim carries a verdict (`verified`/`not verified`/`inconclusive`), a trust-ladder rung, and a runnable proof command.

Referenced skills: `research-this` (`../research-this/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's prove-it-works principle and the verdicts of its figure-it-out skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
