---
name: find-it
description: "Replicate bugs deterministically from provided or correlated real data (logs, traces, metrics, monitoring, usage analytics) and full failure-environment conditions across the end-to-end path, collect runtime evidence (<file>_DEBUG_<shorthash>.<type>) preferring built-in language debuggers then astack tools then third-party tools, shrink the repro before narrowing root causes (binary search/bisect, live dumps, profile pairs), and clean all debug artifacts once fixed. Use for suspected bugs, failing tests, flakes, hangs, leaks, or slowdowns."
---

# Find it

Replicate a bug from real correlated data and the full environment of conditions that produced it, collect targeted runtime evidence, shrink the reproduction to the smallest deterministic failing case **before** diagnosing, narrow its root cause with runtime evidence, and leave zero debug artifacts behind once fixed.

## 1. Replicate the real scenario, data, and environment first

- **Never guess inputs—use correlated real data:** build the repro from inputs, payloads, queries, and cases provided by the user/lead or extracted from logs, traces, metrics, monitoring, telemetry, and usage analytics scoped to the bug path.
- **Replicate the whole failure environment across the full path:** recreate the exact conditions correlated with the error—not just function arguments or SQL rows—including runtime versions, OS and CPU architecture, memory/CPU/disk/FD pressure, network behavior (latency, loss, resets, protocol/HTTP version), config/flags, load/concurrency, and correlated upstream/downstream systems (not exhaustive; match reality first, then strip variables in Section 4).
- **Measure frequency & test `main`:** record the real failure rate (source, window, sample count) for **prove-it** and flaky bisects. Run the scenario on `main` first: if it behaves, log one line and stop; if `main` already fails, isolate it separately (**leave-it-better**) only when it blocks your work.
- Failing test lists are not deliverables, and "hard to test" is not an excuse—make the failure observable.

## 2. Tool preference order & capture naming

Always reach for tools in this order:
1. **Built-in language and runtime debuggers first** (e.g., `pdb`/`faulthandler`/`tracemalloc`/`cProfile`; `go tool pprof`/`go tool trace`/`delve`; `--inspect`/V8 profiler; `lldb`/`gdb`/sanitizers; `jstack`/`jfr`; browser DevTools).
2. **astack tools and skills next** (**prove-it**, **test-drive** `drive-<app>` flows, **show-the-states** / `astack-statechart`, **benchmarking**, and configured `astack-tools` / `werkflow` helpers).
3. **Third-party tools last**, only when built-in and astack tools don't expose the signal.

Save **every** collected debug artifact as **`<file>_DEBUG_<shorthash>.<type>`** (e.g., `auth_DEBUG_a1b2c3d.log`, `server_DEBUG_a1b2c3d.stderr`, `checkout_DEBUG_9f0e1d2.png`, `api_DEBUG_4c5d6e7.trace`, `worker_DEBUG_4c5d6e7.prof`, `flow_DEBUG_8e7f6a5.har`). Keep captures untracked and never write secrets, tokens, or PII into them (**no-leaked-secrets**).

## 3. Signals and tools (helpful starting set, not exhaustive)

- **Logs & `stdout`/`stderr` capture:** split `stdout` and `stderr` with timestamps and exit codes (`tee`), enable targeted debug levels for only the suspect module, and preserve correlation/request IDs.
- **OpenTelemetry (OTel) tracing & HTTP/1.1 / HTTP/2 / HTTP/3 inspection:** enable OTel spans and `traceparent` propagation, export to console/OTLP capture, and inspect HTTP/2 & HTTP/3 streams, headers, trailers, and resets (`curl --http2`/`--http3`, proxy captures, `tshark`).
- **Screenshots & browser/UI captures:** use Playwright (screenshots, trace zips, HAR network logs, console errors) or your repo's **test-drive** `drive-<app>` flow for visual, layout, or client-side failures.
- **Telemetry & metrics:** sample counters, histograms, queue depths, retry/error rates, GC pauses, RSS/heap, and open FDs/sockets across the failure window.
- **Profiling & live dumps:** capture CPU flamegraphs (`perf`, `py-spy`, `samply`, `pprof`), allocation/lock profiles, stack/thread/goroutine/task dumps, open FDs/sockets, or syscall/network probes (`strace`, `lsof`, `tcpdump`) **before** restarting a stuck process.

## 4. Shrink the repro before diagnosing

Before narrowing the root cause or proposing a fix, reduce the confirmed failure to the smallest standalone case that still triggers the exact same error, panic, or wrong output—shrinking first removes noise and cuts the suspect space:

- **Dependency & I/O removal:** strip external libraries, network calls, and file reads to inline data.
- **Delta debugging (bisection):** comment out or delete code in halves while verifying the exact same error or panic still triggers.
- **Type & logic simplification:** replace complex structs, generics, or async runtimes with minimal primitives and synchronous blocks.
- **Binary search on payload:** split a triggering file, query, or payload in half repeatedly to pinpoint the exact malformed record or byte sequence.
- **Thread & core pinning:** pin execution to one CPU core (`taskset -c 0`) or set thread pool size to `1` to separate pure logic bugs from hardware parallelism.
- **Record-and-replay:** capture a failing trace with `rr` (Linux) or Pernosco to step backward from the crash and inspect exact memory state without re-triggering a rare race.
- **State serialization (snapshot):** dump in-memory state right before the failing function runs, then load it in a tiny standalone harness to bypass long setup or ingestion.
- **Environment & flag stripping:** reset compiler flags (debug vs. release optimizations), disable custom allocators (`jemalloc`/`mimalloc`), and run in a clean container to rule out host drift.
- **Feature-flag pruning:** disable Cargo features, compile-time macros, or optional modules one by one to isolate which subsystem introduces the fault.

## 5. Narrow the root cause with runtime evidence

- **Binary search & `git bisect`:** cut history (`git bisect run`) or execution space in half with one discriminating observation using the shrunk repro.
  - **Flaky repros:** never bisect a flake on a single pass—for failure rate $p$, require $n \ge \lceil \ln(1-c)/\ln(1-p) \rceil$ consecutive clean runs before labeling `good` at confidence $c$ (e.g., $p = 10\%$ at $c = 95\%$ needs $29$ passes; any single failure is `bad`).
  - **Performance regressions:** run a **three-way Sobel–Wald dual SPRT** (`good` vs `mid` vs `bad`, **benchmarking**) with depth-scaled $\alpha \approx \alpha_{\text{total}}/(2K)$, interleaved `(good, candidate, bad)` measurements per commit, and a confirmation pass before stopping on `middle` (reserve `git bisect skip` for commits that cannot build/run).
- **Captured profiles & live symptoms:** read top-down from the hot path, separate waiting from CPU work, map hot frames to `file:line`, and diagram unexpected state transitions (**show-the-states**). A single capture gives at most a hypothesis—confirm the cause with a **before/after pair**.
- **One falsifiable hypothesis at a time:** state the hypothesis and what would disprove it before testing; **revert every edit or instrumentation a disproved hypothesis motivated immediately**, and record each rejected theory along with the exact evidence that disproved it. After two consecutive disproved hypotheses, stop and interrogate the diagnosis (**challenge**).

## 6. Hand off and clean up

Hand the shrunk repro, root cause (`file:line`), evidence trail, and all **rejected theories** (what was tested and what disproved each) to **fix-it** and the lead (so they are logged as `decided:` entries and never re-tested; never leave speculative changes behind). Prune stale `<file>_DEBUG_<shorthash>.<type>` files mid-investigation as needed, and **always** run **cleanup** once the issue is fixed so every `<file>_DEBUG_<shorthash>.<type>` capture and temporary debug hook is removed.

Referenced skills: `prove-it` (`../prove-it/SKILL.md`), `leave-it-better` (`../leave-it-better/SKILL.md`), `test-drive` (`../test-drive/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `challenge` (`../challenge/SKILL.md`), `fix-it` (`../fix-it/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's bug-fix, live-symptom, and profile diagnosis playbooks (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
