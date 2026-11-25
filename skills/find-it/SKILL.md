---
name: find-it
description: "Replicate bugs deterministically from correlated real data and full failure-environment conditions, collect runtime evidence (<file>_DEBUG_<shorthash>.<type>), shrink the repro before diagnosing, narrow root causes with bisect/dumps/profiles, and clean debug artifacts. Use inside bugbash investigators, workers, or single-agent hosts."
disable-model-invocation: true
---

# Find it

Replicate the bug from real data and environment conditions, **shrink the repro before diagnosing**, narrow the root cause with runtime evidence, and remove every debug artifact afterward.

**In Go/Lead mode with subagents:** do not solo-debug reported issues—route to **bugbash** so read-only reviewers run **find-it** (risk-scaled by vector). Run **find-it** directly only as a spawned investigator/worker or on a single-agent host.

## 1. Replicate real data and environment first

- **Acquire correlated real data—never block when unavailable:** use **analyze-environment** (`TOOLS.md`) and **rtfm** to pull failure evidence via read-only probes from attachments, CI logs, observability platforms (logs, traces, metrics, error trackers), or a local dev stack with traffic emulation.
- **Build missing acquisition tools or skills (**automate-this**, **test-drive**):** if nothing can fetch or emulate the signal, write a secret-safe (**no-leaked-secrets**) helper script or skill. Reviewers put scratch fetchers in their repro folder; publish usage in your report for reuse.
- **Fall back without stalling:** if real data stays unavailable, build the closest realistic case from code paths, schemas, and symptoms. Mark it inferred (**decisions-in-plain-words**) and refine it if real data arrives.
- **Match the whole failure environment:** match runtime versions, OS and CPU architecture, memory/CPU/disk/FD pressure, network behavior (latency, loss, resets, HTTP version), flags, concurrency, and upstream/downstream systems. Strip variables later in Section 4.
- **Measure frequency and check `main`:** record failure rate (source, window, sample count) for **prove-it**. Run the repro on `main` first: if `main` behaves, log one line and move on; if `main` already fails, isolate separately (**leave-it-better**) only when it blocks you.

Failing test lists are not deliverables, and "hard to test" is not an excuse.

## 2. Tool preference order & capture naming

Reach for tools in this order:

1. **Built-in language and runtime debuggers first:** `pdb`/`faulthandler`/`tracemalloc`/`cProfile`, `go tool pprof`/`delve`, `--inspect`/V8 profiler, `lldb`/`gdb`/sanitizers, `jstack`/`jfr`, browser DevTools.
2. **astack tools and skills next:** **prove-it**, **test-drive** (`drive-<app>`), **show-the-states** (`astack-statechart`), **benchmarking**, `astack-tools`.
3. **Third-party tools last,** only when built-in and astack tools cannot expose the signal.

Name every capture **`<file>_DEBUG_<shorthash>.<type>`** (e.g., `auth_DEBUG_a1b2c3d.log`, `worker_DEBUG_4c5d6e7.prof`). Keep captures untracked and free of secrets or PII (**no-leaked-secrets**).

## 3. Starting signals (illustrative, not exhaustive)

- **Logs & stdio:** split `stdout` and `stderr` with timestamps (`tee`), enable debug logging only on the suspect module, and preserve request IDs.
- **Tracing & HTTP:** capture OpenTelemetry spans and `traceparent` headers, and inspect HTTP/1.1, HTTP/2, or HTTP/3 streams (`curl`, proxies, `tshark`; use **net-trace** for deeper packet, DNS, TLS, firewall, or flow-log tracing).
- **UI & browser:** capture Playwright screenshots, trace zips, HAR files, and console errors (or run `drive-<app>`).
- **Telemetry & metrics:** sample counters, queue depths, retry/error rates, GC pauses, RSS/heap, and open FDs.
- **Profiles & live dumps:** grab CPU/alloc/lock flamegraphs (`perf`, `py-spy`, `samply`, `pprof`), stack/goroutine dumps, and `strace`/`lsof`/`tcpdump` **before** restarting a stuck process.

## 4. Shrink the repro before diagnosing

Reduce the confirmed failure to the smallest standalone repro before proposing any root cause, because shrinking strips away noise and cuts the suspect space:

- **Strip dependencies & I/O:** inline files, network replies, and external libraries.
- **Delta debugging:** remove code in halves while confirming the exact same failure still triggers.
- **Simplify types & control flow:** replace complex structs or async runtimes with minimal primitives.
- **Bisect the payload:** halve triggering inputs to locate the exact bad record or byte sequence.
- **Pin concurrency:** run on one core (`taskset -c 0`) or pool size `1` to separate logic bugs from races.
- **Record-and-replay / snapshots:** capture rare races with `rr` or dump pre-call state into a tiny harness.
- **Strip flags & features:** reset compiler/allocator flags, disable optional features, and run in a clean container.

## 5. Narrow the root cause with runtime evidence

- **Binary search & `git bisect`:** halve history (`git bisect run`) or execution paths with the shrunk repro.
  - **Flaky repros:** never trust one clean run. For failure rate $p$, require $n \ge \lceil \ln(1-c)/\ln(1-p) \rceil$ clean runs before marking `good` at confidence $c$ (e.g., $p = 10\%$ at $95\%$ needs $29$ clean runs; any single failure is `bad`).
  - **Performance regressions:** run a three-way Sobel–Wald dual SPRT (**benchmarking**) with interleaved `(good, candidate, bad)` runs and a confirmation pass before stopping on `middle`.
- **Profiles & state charts:** read hot paths top-down, separate waiting from CPU work, map frames to `file:line`, and diagram bad transitions (**show-the-states**). One capture is only a hypothesis—confirm with a **before/after pair**.
- **One falsifiable hypothesis at a time:** state the hypothesis and disproof test before running. Revert any edit a disproved hypothesis motivated immediately, and record the rejected theory with its evidence. After **two consecutive disproved hypotheses**, stop and run **challenge**.

## 6. Hand off and clean up

Pass the shrunk repro, root cause (`file:line`), evidence trail, and all **rejected theories** to **fix-it** and the lead so dead ends get logged as `decided:` and never repeated. Run **cleanup** once fixed so every `<file>_DEBUG_<shorthash>.<type>` artifact and debug hook is deleted.

<!-- Adapts pstack's bug-fix, live-symptom, and profile diagnosis playbooks (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
