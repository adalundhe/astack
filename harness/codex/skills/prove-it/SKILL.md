---
name: prove-it
description: "Verify claims against the real artifact (not proxies), rank evidence on the trust ladder, challenge weak claims, and provide runnable proof. Use before calling work done or reporting/challenging any claim."
---

# Prove it

Verify results on the real system, back claims with the strongest evidence available, and give the person a way to rerun the proof.

## Verify the real thing

Check the actual artifact: run the feature, inspect the real output, read the actual diff. Proxies prove nothing (file timestamps, another agent's summary, cached output, "it compiles"). If a check fails unexpectedly—or passes suspiciously easily—audit the check itself before assuming the system is broken or fixed. Script checks so anyone can rerun them, and keep outputs accessible.

Classify every verification as **verified**, **not verified**, or **inconclusive**. Never treat inconclusive as a pass, and report negative results openly.

## The trust ladder

From weakest to strongest evidence:

1. Your own (or another agent's) reasoning or memory.
2. Unverified code you just wrote, or results backed only by mocks/proxies.
3. Existing code or docs you read without running.
4. Running the real system—tests, benchmarks, A/B comparisons, or reference implementations.
5. Published reference datasets, peer-reviewed research, and foundational specifications.

Push every claim as high up the ladder as practical and state which rung it rests on. Challenge weak claims (yours or another agent's) by asking which rung they stand on and bringing evidence from a higher one.

## Show your work

Don't assume the person shares your context. Present findings in order:

1. **Problem:** brief restatement of what you investigated.
2. **Hypothesis or solution:** what you tested or built, concisely.
3. **Method:** the reasoning and concrete steps taken.
4. **Evidence:** raw data, outputs, profiles, traces, or benchmarks.

Include something the person can run directly (a command, script, minimal repro, or demo)—for failures as well as successes.

<!-- Adapts pstack's prove-it-works principle and the verdicts of its figure-it-out skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
