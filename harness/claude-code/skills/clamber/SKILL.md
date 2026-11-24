---
name: clamber
description: "Iteratively improve performance and minimize variance (sigma) in small measured steps: baseline median and standard deviation, hill-climb by >=1 sigma per step while tightening variance, sanity-check against Amdahl bounds, enforce a minimum attempt floor, commit gains, and revert regressions. Use when significant optimization is needed."
disable-model-invocation: true
---

# Clamber

Improve performance and tighten measured variance in small, grounded steps—committing each gain and reverting anything that regresses.

## Before the first step

1. **Work, then robust, then fast.** Only optimize code that already works and passes its tests. Tests must pass before and after every step (**tests-assert-behaviour**).
2. **Define the target.** Specify each metric to improve, the target number, and how it's measured (CPU, peak memory/allocations/cache misses/page faults, disk I/O, network calls/wire bytes, concurrent throughput/contention, binary/package size, or any requested metric).
3. **Reproduce realistically.** Use realistic data sizes, history, state, and concurrency. If you can't reproduce the bottleneck, fix the workload first.
4. **Baseline every important metric and its $\sigma$** (**benchmarking**), not just the primary target, so a win in one metric can't hide a regression in another. Record baseline median, standard deviation ($\sigma$), p99/spread, environment, and commands, and verify the harness detects regressions and executes real work.
5. **Profile and trace** to see where time, memory, I/O, bytes, and jitter actually go (**diagnose**).
6. **Keep an experiment log** of every attempt: hypothesis, change, before/after median and $\sigma$, Amdahl check, test status, and kept/reverted outcome.

## Each step (grounded $\sigma$-step hill-climbing & variance reduction)

Treat **reducing measured variance ($\sigma$)** as equally important to moving the baseline median—jitter from allocations, GC pauses, lock convoys, page faults, or I/O stalls caps both p99 and your ability to measure further wins.

Pick the largest remaining bottleneck (or largest source of $\sigma$/tail variance) and ask these in strict order, acting on the first "yes":

1. **Can we skip the work entirely?**
2. **Can we do less of it?**
3. **Can we eliminate variance/jitter sources?** (Remove allocation spikes, lock contention, cold-path falls, cache-line bouncing, or unbuffered I/O.)
4. **Can we do it more efficiently?** Fewer CPU cycles and allocations, better cache/memory layout, fewer page faults, less disk churn, fewer bytes; SIMD/vectorization only after the plain version is proven correct.
5. **Can we defer it or move it off the hot path?**
6. **Can we parallelize it?**

Then:

1. **Set a $\sigma$-grounded step goal:** target moving the metric by **at least one current standard deviation ($\ge 1\sigma$)** (as the step goal / MDE, sized with enough runs for $\ge 80\%$ power) or materially shrinking $\sigma$ / tail spread itself, and state the exact mechanism (e.g., "pool scratch buffers to cut GC pause spikes driving $\sigma$", not "try caching").
2. **Make one isolated change.** Don't stack untested ideas.
3. **Run the tests.** User-visible behavior must stay identical (**never-trade-functionality**).
4. **Re-measure all baseline metrics (median and $\sigma$).**
   - **Sanity-check the gain:** verify the speedup stays within the Amdahl bound ($1/(1-f)$ where $f$ includes both active CPU work **and waiting**—locks, I/O, queueing, GC—from wall-clock profiles) and confirm outputs were genuinely computed.
   - Keep the change only if it passes **benchmarking**'s dual acceptance bar—either a significant location win (95% Mann-Whitney U / bootstrap median CI) **or** a significant spread win (Brown–Forsythe test and/or 95% bootstrap CI on $\sigma_{\text{new}}/\sigma_{\text{base}} < 1$ or tail-spread ratio $< 1$, with median non-regressed)—without regressing other metrics, then recompute $\sigma$ on the new baseline for the next step.
5. **Commit or revert cleanly.** Commit each kept win on its own with before/after median and $\sigma$ in the commit message so later regressions can be bisected/reverted individually. Revert failed attempts completely.
6. **Log the attempt** and repeat.

If you have several independent ideas, test them in parallel in separate worktrees (**ab-test**).

## Finish

- **Agreed minimum attempt floor:** don't stop after a lucky early win, and don't pick a magic constant (**no-picked-constants**). Agree the minimum number of distinct measured attempts with the person before starting (or derive and record the floor in the experiment log from the task's time budget and remaining profiled headroom), and complete that floor across real bottlenecks and variance sources unless you hit a proven hardware/algorithmic ceiling backed by profiles and **research-this**.
- **Break through plateaus:** if incremental tweaks stall short of the goal, try another optimization category, attack $\sigma$/variance directly, combine near misses, reread the hot path, or prototype alternative architectures (**explore-the-limits**).
- **Know when to stop:** stop once the target (both baseline and variance stability) is met and the minimum attempt floor is satisfied. Before concluding further gains require trading functionality, run **research-this** and **explore-the-limits** to verify no compliant design exists; only then present the best compliant result, what limits it, and the trade-off with numbers to the person (**never-trade-functionality**, **decisions-in-plain-words**). Never relax the goal to declare victory.
- **Report:** baseline vs. final median and $\sigma$ for every metric, steps kept and reverted, the full log, the current bottleneck, and the best next lead (**prove-it**).

Referenced skills: `tests-assert-behaviour` (`${CLAUDE_SKILL_DIR}/../tests-assert-behaviour/SKILL.md`), `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `diagnose` (`${CLAUDE_SKILL_DIR}/../diagnose/SKILL.md`), `never-trade-functionality` (`${CLAUDE_SKILL_DIR}/../never-trade-functionality/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `no-picked-constants` (`${CLAUDE_SKILL_DIR}/../no-picked-constants/SKILL.md`), `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `explore-the-limits` (`${CLAUDE_SKILL_DIR}/../explore-the-limits/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's Hillclimb playbook (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
