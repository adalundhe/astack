---
name: prove-it
description: "Verify claims against the real artifact (not proxies) with deterministic reproduction, empirically measured occurrence frequency (from logs, traces, telemetry, monitoring, metrics, or usage analytics), trust-ladder ranking, and runnable proof. Use before calling work done or reporting/challenging any claim."
disable-model-invocation: true
---

# Prove it

Verify results on the real system with deterministic reproduction, measure real occurrence frequency from telemetry and usage data, back claims with the strongest evidence available, and give the person a way to rerun the proof.

## Verify the real thing

Check the actual artifact: run the feature, inspect the real output, read the actual diff. Proxies prove nothing (file timestamps, another agent's summary, cached output, "it compiles"). If a check fails unexpectedly—or passes suspiciously easily—audit the check itself before assuming the system is broken or fixed. Script checks so anyone can rerun them, and keep outputs accessible.

Classify every verification as **verified**, **not verified**, or **inconclusive**. Never treat inconclusive as a pass, and report negative results openly.

## Deterministic reproduction & empirical frequency

- **Deterministic reproduction:** prove behavior with a repeatable repro—fixed inputs, explicit seeds, controlled clocks/schedules, and exact failure conditions—that fails reliably before the change and passes reliably after. One lucky green run proves nothing.
- **Empirical frequency (**no-picked-constants**):** measure how often a failure or path occurs from accessible logs, traces, telemetry, monitoring, metrics, or usage analytics (citing source, time window, and sample count)—never invent rates or hand-wave "rare/common". If telemetry isn't accessible, don't block or guess: mark frequency as unmeasured and prove behavior deterministically.
- **Intermittent faults:** eliminate nondeterminism structurally (seeded scheduler, pinned clock, fault injection) wherever possible; otherwise compute the required clean-run count from the measured failure rate $p$ ($n \ge \lceil \ln(1-c)/\ln(1-p)\rceil$, **find-it**).

## The trust ladder

From weakest to strongest evidence (aligned with **research-this** source trust weights):

1. Your own (or another agent's) reasoning or memory.
2. Unverified code you just wrote, or results backed only by mocks/proxies.
3. Existing code or docs you read without running.
4. Authoritative external references: foundational specifications, standards, official docs, peer-reviewed research, and published reference datasets (weights `0.85–0.90` in **research-this**).
5. Running and measuring the real system—end-to-end tests, live reproductions, controlled benchmarks, and A/B comparisons on the actual artifact (strongest proof of what this system does; weight `0.95` in **research-this**).

Push every claim as high up the ladder as practical and state which rung it rests on. Challenge weak claims (yours or another agent's) by asking which rung they stand on and bringing evidence from a higher one.

## Show your work

Don't assume the person shares your context. Present findings in order:

1. **Problem:** brief restatement of what you investigated.
2. **Hypothesis or solution:** what you tested or built, concisely.
3. **Method & conditions:** the reasoning, concrete steps, exact reproduction conditions/environment, and—where relevant—the empirically measured frequency (source, window, sample count).
4. **Evidence:** raw data, outputs, profiles, traces, telemetry, or benchmarks.

Include something the person can run directly (a deterministic command, script, minimal repro, or demo)—for failures as well as successes.

<!-- Adapts pstack's prove-it-works principle and the verdicts of its figure-it-out skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
