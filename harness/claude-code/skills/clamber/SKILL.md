---
name: clamber
description: "Hill-climb performance and cut variance (sigma) in measured steps, keeping wins and reverting losses. Use when optimizing latency, throughput, or jitter."
disable-model-invocation: true
---

# Clamber

Improve performance and tighten measured variance in small, grounded steps. Commit each verified gain and revert anything that regresses.

## Before the first step

1. **Work, then robust, then fast.** Only optimize working code whose tests pass before and after every step (`tests-assert-behaviour`).
2. **Define the target:** name each metric (CPU, memory/allocs, cache misses, I/O, throughput, binary size), the target number, and how it is measured.
3. **Reproduce realistically:** use realistic data sizes, state, and concurrency. Fix the workload first if it cannot reproduce the bottleneck.
4. **Baseline every important metric and its $\sigma$ (**benchmarking**):** record median, $\sigma$, p99/spread, environment, and commands across all key metrics so one win cannot hide a regression elsewhere. Confirm the harness executes real work.
5. **Profile and trace (**find-it**):** locate where time, memory, I/O, and jitter actually go.
6. **Keep an experiment log:** record hypothesis, change, before/after median and $\sigma$, Amdahl check, test result, and kept/reverted outcome for every attempt.

## Each step ($\sigma$-grounded hill-climbing)

Treat **reducing variance ($\sigma$)** as equally important to moving the median, because jitter from allocations, GC pauses, lock convoys, or page faults caps p99 and blinds further measurements.

Pick the largest bottleneck or $\sigma$ source and ask in strict order, because removing work always beats micro-optimizing unnecessary work. Act on the first "yes":

1. **Can we skip the work entirely?**
2. **Can we do less of it?**
3. **Can we cut variance/jitter sources?** (Allocation spikes, lock contention, cache-line bouncing, unbuffered I/O.)
4. **Can we do it more efficiently?** (Fewer cycles/allocs, tighter layout, fewer page faults or wire bytes; SIMD only after scalar is proven.)
5. **Can we defer it off the hot path?**
6. **Can we parallelize it?**

Then execute one clean cycle:

1. **Set a $\sigma$-grounded goal:** target moving the metric by $\ge 1\sigma$ (sized for $\ge 80\%$ power) or shrinking $\sigma$ / tail spread. State the exact mechanism.
2. **Make one isolated change.** Never stack untested ideas, because stacking hides which change helped or hurt.
3. **Run the tests.** User-visible behavior must stay identical (**never-trade-functionality**).
4. **Re-measure all baseline metrics (median and $\sigma$):**
   - Check the speedup against the Amdahl bound ($1/(1-f)$, including CPU and wait time from wall-clock profiles) and verify outputs were genuinely computed.
   - Keep only if it clears **benchmarking**'s acceptance tests for location, dispersion, or tail spread with zero regressions elsewhere. Recompute $\sigma$ on the new baseline.
5. **Commit or revert cleanly:** commit each kept win alone with before/after median and $\sigma$ in the message for clean bisection. Revert failed attempts completely.
6. **Log the attempt** and repeat.

Test independent ideas in parallel workspaces (**ab-test**). Lead may pair `clamber` with **redteam** so kept optimizations clear vectored review for correctness and races.

## Finish

- **Agreed minimum attempt floor:** agree the minimum number of distinct measured attempts upfront, or derive it from time budget and profiled headroom (never pick a magic number per `no-picked-constants`). Complete the floor unless profiles and **research-this** prove a hardware or algorithmic ceiling.
- **Break plateaus:** switch optimization categories, attack $\sigma$ directly, combine near misses, reread the hot path, or prototype new designs (**swarm-hypothesis**).
- **Know when to stop:** stop once the target and attempt floor are met. Before claiming further gains require trading functionality, run **research-this** and **swarm-hypothesis**. Only then present the best compliant result and trade-off with numbers (**never-trade-functionality**, **decisions-in-plain-words**). Never relax the goal.

**Reply (`prove-it`):** report baseline vs. final median and $\sigma$ for every metric, kept/reverted steps, experiment log, current bottleneck, and best next lead.

Referenced skills: `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `find-it` (`${CLAUDE_SKILL_DIR}/../find-it/SKILL.md`), `never-trade-functionality` (`${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `redteam` (`${CLAUDE_SKILL_DIR}/../redteam/SKILL.md`), `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `swarm-hypothesis` (`${CLAUDE_SKILL_DIR}/../swarm-hypothesis/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
