---
name: find-it
description: "Replicate bugs from real data, shrink the repro before diagnosing, prove root causes, and clean artifacts. Use inside bugbash investigators, workers, or single-agent hosts."
disable-model-invocation: true
---

# Find it

Replicate the bug from real data and environment conditions, then **shrink the repro before diagnosing**. Narrow the root cause with runtime evidence and delete every debug artifact afterward.

**In Go/Lead mode with subagents:** never solo-debug reported issues—route to **bugbash** so read-only reviewers run `find-it`. Run `find-it` directly only as a spawned investigator, worker, or single-agent host.

## 1. Replicate real data and environment first

- **Acquire correlated real data—never block when unavailable:** use `TOOLS.md` (`analyze-environment`) and `rtfm` to run read-only probes. Pull evidence from attachments, CI logs, observability tools, or a local stack with traffic emulation.
- **Build missing acquisition tools or skills (`automate-this`, `test-drive`):** write a secret-safe (`no-leaked-secrets`) fetcher or helper when none exists. Save standalone repros and scratch fetchers under `~/.astack/<project>/repros/<repro>/` (`astack-tools repros path <project> <repro> --ensure`). Report usage for reuse.
- **Fall back without stalling:** if real data stays unavailable, build the closest case from code paths, schemas, and symptoms. Mark it inferred (`decisions-in-plain-words`) and refine it if real data arrives.
- **Match the whole failure environment:** match runtime versions, OS, CPU architecture, and resource pressure (memory, CPU, disk, FDs). Also match network behavior, flags, concurrency, and dependencies, then strip variables in Section 4.
- **Measure frequency and check `main`:** record failure rate (source, window, sample count) for `prove-it`. Run the repro on `main` first; isolate preexisting `main` failures (`leave-it-better`) only if they block you.

Failing test lists are not deliverables, and "hard to test" is not an excuse.

## 2. Tool preference order & capture naming

Reach for tools in this order, because built-ins carry zero setup risk and astack tools already format clean evidence:

1. **Built-in language and runtime debuggers first:** `pdb`/`faulthandler`/`tracemalloc`/`cProfile`, `go tool pprof`/`delve`, `--inspect`/V8 profiler, `lldb`/`gdb`/sanitizers, `jstack`/`jfr`, browser DevTools.
2. **astack tools and skills next:** `prove-it`, `test-drive` (`drive-<app>`), `show-the-states` (`astack-statechart`), **benchmarking**, `astack-tools`.
3. **Third-party tools last,** only when built-in and astack tools cannot expose the signal.

Name temporary workspace captures **`<file>_DEBUG_<shorthash>.<type>`** (e.g., `auth_DEBUG_a1b2c3d.log`). Persist retained logs, traces, and metrics under `$HOME/.astack/<project_name>/logging/<logs|traces|metrics>/[FILE_YYYY_MM_DD_HH_MM_SS]` (`astack-tools logging path`). Keep all captures untracked and free of secrets or PII (`no-leaked-secrets`).

## 3. Starting signals (illustrative, not exhaustive)

- **Logs & stdio:** split `stdout` and `stderr` with timestamps (`tee`), enable debug logs on the suspect module, and keep request IDs.
- **Tracing & HTTP:** capture OpenTelemetry spans and `traceparent` headers, and inspect HTTP/1.1, HTTP/2, or HTTP/3 streams (`curl`, proxies, `tshark`). Use **net-trace** for deeper packet, DNS, TLS, firewall, or flow-log tracing.
- **UI & browser:** capture Playwright screenshots, trace zips, HAR files, and console errors (or run `drive-<app>`).
- **Telemetry, metrics, & trace forensics:** sample counters, queue depths, retry/error rates, GC pauses, RSS/heap, and open FDs. For large logs or trace dumps, load structured events into SQLite to query latency tails, span trees, and cross-request correlations instead of grepping blindly.
- **Profiles, heap retainers, & live dumps:** grab CPU/alloc/lock flamegraphs (`perf`, `py-spy`, `samply`, `pprof`), heap snapshots with retainer chains and steady-state allocation diffs for leaks, and stack/goroutine dumps. Capture `strace`/`lsof`/`tcpdump` **before** restarting a stuck process.

## 4. Shrink the repro before diagnosing

Reduce the confirmed failure to the smallest standalone repro before proposing a root cause, because shrinking removes noise and cuts the suspect space:

- **Strip dependencies & I/O:** inline files, network replies, and external libraries.
- **Delta debugging:** remove code in halves while confirming the same failure still triggers.
- **Simplify types & control flow:** replace complex structs or async runtimes with minimal primitives.
- **Bisect the payload:** halve triggering inputs to locate the exact bad record or byte sequence.
- **Pin concurrency:** run on one core (`taskset -c 0`) or pool size `1` to separate logic bugs from races.
- **Record-and-replay / snapshots:** capture rare races with `rr` or dump pre-call state into a tiny harness.
- **Strip flags & features:** reset compiler/allocator flags, disable optional features, and run in a clean container.

## 5. Narrow the root cause with runtime evidence

- **Binary search & `git bisect`:** halve history (`git bisect run`) or execution paths with the shrunk repro.
  - **Flaky repros:** never trust one clean run or raw point estimates. Compute a conservative 95% lower confidence bound $p_{\text{low}}$ on the measured failure rate $k/m$ (e.g., Clopper–Pearson: $3/20$ gives $p_{\text{low}} \approx 0.032$, needing $\sim 93$ clean runs at $\alpha=0.05$, not $19$). Across a $K$-step bisect ($K \approx \lceil\log_2 N\rceil$), control family-wise error with per-step $\alpha_{\text{step}} = \alpha / K$ (or $\alpha / (2K)$ two-sided): $n \ge \lceil \ln(\alpha_{\text{step}})/\ln(1-p_{\text{low}}) \rceil$. Any single failure marks `bad`.
  - **Performance regressions:** bisect with interleaved alternating `(good, candidate)` runs sized from baseline median and $\sigma$ (**benchmarking**), applying per-step $\alpha / (2K)$ across $K$ bisect steps before marking a commit `good` or `bad`.
- **Profiles & state charts:** read hot paths top-down, separate waiting from CPU work, map frames to `file:line`, and diagram bad transitions (`show-the-states`). One capture is only a hypothesis—confirm with a **before/after pair**.
- **One falsifiable hypothesis at a time:** state the hypothesis and disproof test first. Record every rejected theory with evidence. Workers and single-agent hosts revert disproved edits immediately. Read-only reviewers write only under `~/.astack/<project>/repros/` and `~/.astack/<project>/reviews/`. After **two consecutive disproved hypotheses**, stop and run **challenge**.

## 6. Hand off and clean up

Hand off the shrunk repro, root cause (`file:line`), evidence, and **rejected theories** to **fix-it** and the lead. Logging dead ends as `decided:` stops repeats. Run **cleanup** once fixed to delete every `<file>_DEBUG_<shorthash>.<type>` file and debug hook.

**Done when:**
- the bug reproduces deterministically from a shrunk standalone repro, or (for confirmed intermittent faults) clears the flaky-repro statistical bar above;
- runtime evidence pins the root cause to exact `file:line`;
- every rejected theory is recorded with its disproof evidence;
- all `<file>_DEBUG_<shorthash>.<type>` files and temporary hooks are cleaned up.

Referenced skills: `bugbash` (`../bugbash/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `net-trace` (`../net-trace/SKILL.md`), `challenge` (`../challenge/SKILL.md`), `fix-it` (`../fix-it/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's bug-fix, live-symptom, and profile diagnosis playbooks (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
