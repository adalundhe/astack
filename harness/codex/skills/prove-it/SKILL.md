---
name: prove-it
description: "Verify claims against the real artifact (not proxies), shrink bug reproductions to the minimal failing case, rank evidence on the trust ladder, challenge weak claims, and provide runnable proof. Use before calling work done, when shrinking a failing repro, or when reporting/challenging any claim."
---

# Prove it

Verify results on the real system, shrink bug reproductions to the smallest case that still fails, back claims with the strongest evidence available, and give the person a way to rerun the proof.

## Verify the real thing

Check the actual artifact: run the feature, inspect the real output, read the actual diff. Proxies prove nothing (file timestamps, another agent's summary, cached output, "it compiles"). If a check fails unexpectedly—or passes suspiciously easily—audit the check itself before assuming the system is broken or fixed. Script checks so anyone can rerun them, and keep outputs accessible.

Classify every verification as **verified**, **not verified**, or **inconclusive**. Never treat inconclusive as a pass, and report negative results openly.

## Shrink the repro

When reproducing a bug or failure, shrink it to the smallest standalone case that still triggers the exact same error, panic, or wrong output before diagnosing or fixing:

- **Dependency & I/O removal:** strip external libraries, network calls, and file reads to inline data.
- **Delta debugging (bisection):** comment out or delete chunks of code in halves while verifying the exact same error or panic still triggers.
- **Type & logic simplification:** replace complex structs, generics, or async runtimes with minimal primitives and synchronous blocks.
- **Binary search on payload:** when a file, query, or payload triggers the bug, split the data in half repeatedly to pinpoint the exact malformed record or byte sequence.
- **Thread & core pinning:** pin execution to a single CPU core (`taskset -c 0`) or set thread pool sizes to `1` to separate pure logic bugs from true hardware parallelism.
- **Record-and-replay:** capture a failing execution trace with `rr` (Linux) or Pernosco to step backward from the crash and inspect exact memory state without re-triggering a rare race.
- **State serialization (snapshot):** dump in-memory state right before the failing function executes, then load it in a tiny standalone harness to bypass long setup or ingestion.
- **Environment & flag stripping:** reset compiler flags (debug vs. release optimizations), disable custom allocators (`jemalloc`/`mimalloc`), and run in a clean container to rule out host drift.
- **Feature-flag pruning:** disable Cargo features, compile-time macros, or optional modules one by one to isolate which subsystem introduces the fault.

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
3. **Method:** the reasoning and concrete steps taken.
4. **Evidence:** raw data, outputs, profiles, traces, or benchmarks.

Include something the person can run directly (a command, script, minimal repro, or demo)—for failures as well as successes.

Referenced skills: `research-this` (`../research-this/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's prove-it-works principle and the verdicts of its figure-it-out skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
