---
name: prove-it
description: "Verify claims on the real artifact with deterministic repros, measured frequency, and runnable proof. Use before calling work done or reporting/challenging any claim."
---

# Prove it

Verify claims on the real system with deterministic reproduction and measured telemetry frequency. Back every claim with the strongest evidence available, and give the person a runnable proof.

## Verify the real thing

Check the actual artifact: run the feature, inspect real output, and read the actual diff. Proxies prove nothing—timestamps, agent summaries, cached output, or "it compiles" are not proof. When a check fails unexpectedly or passes too easily, audit the check itself first. Script checks so anyone can rerun them, and keep outputs accessible.

Classify every verification as **verified**, **not verified**, or **inconclusive**. Never treat inconclusive as a pass, and report negative results openly.

## Deterministic reproduction & empirical frequency

- **Deterministic reproduction:** prove behavior with a repeatable repro using fixed inputs, explicit seeds, and controlled schedules. It must fail before the change and pass after; one lucky run proves nothing.
- **Empirical frequency (**no-picked-constants**):** measure occurrence rates from accessible logs, traces, telemetry, metrics, or usage analytics. Cite source, time window, and sample count; never guess "rare" or "common". If telemetry is unavailable, mark frequency unmeasured and prove behavior deterministically.
- **Intermittent faults:** eliminate nondeterminism structurally via seeded schedulers, pinned clocks, or fault injection (`find-it`). Otherwise compute clean runs from failure rate `p` via `n >= ceil(ln(1-c)/ln(1-p))`.

## The trust ladder

From weakest to strongest evidence (aligned with **research-this** source trust weights):

1. Your own (or another agent's) reasoning or memory.
2. Unverified code you just wrote, or results backed only by mocks or proxies.
3. Existing code or docs you read without running.
4. Internal data, logs, or telemetry (weight `0.80`), plus specs, official docs, and peer-reviewed papers (`0.85–0.90` in `research-this`).
5. Running and measuring the real system: end-to-end tests, live repros, benchmarks, and A/B comparisons. Direct measurement is the strongest proof (weight `0.95` in `research-this`).

Push every claim as high up the ladder as practical and state its rung. Challenge weak claims by naming their rung and bringing higher-rung evidence.

## Show your work

Don't assume the person shares your context. Present findings in order:

1. **Problem:** brief restatement of what you investigated.
2. **Hypothesis or solution:** what you tested or built, concisely.
3. **Method & conditions:** steps, exact reproduction environment, and measured frequency (source, window, sample count) when relevant.
4. **Evidence:** raw data, outputs, profiles, traces, telemetry, or benchmarks.

Include a deterministic command, script, minimal repro, or demo the person can run—for failures and successes alike.

**Done when:** every claim carries a verdict (`verified`/`not verified`/`inconclusive`), a trust-ladder rung, and a runnable proof command.

Referenced skills: `no-picked-constants` (`../no-picked-constants/SKILL.md`), `research-this` (`../research-this/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's prove-it-works principle and the verdicts of its figure-it-out skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
