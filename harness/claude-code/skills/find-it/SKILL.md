---
name: find-it
description: "Replicate bugs deterministically from provided or correlated real data (logs, traces, metrics, monitoring, usage analytics) and full failure-environment conditions across the end-to-end path, collect runtime evidence (<file>_DEBUG_<shorthash>.<type>) preferring built-in language debuggers then astack tools then third-party tools, shrink the repro before narrowing root causes (binary search/bisect, live dumps, profile pairs), and clean all debug artifacts once fixed. Use for suspected bugs, failing tests, flakes, hangs, leaks, or slowdowns."
disable-model-invocation: true
---

# Find it

Replicate the failure from real data and conditions, capture targeted runtime evidence, shrink the repro **before** diagnosing, narrow the root cause, and clean up every debug artifact once fixed.

## 1. Replicate the real scenario, data, and environment first

- **Actively acquire correlated real data—never block when unavailable:** inspect code, infrastructure, configs, and env vars (**rtfm**) to pull real failure data from any accessible source: user or lead attachments, CI/CD logs and artifacts, monitoring and observability platforms (logs, traces, metrics, error trackers), or a local dev stack driven with repeated runs and traffic emulation.
  - **Build missing acquisition tools or skills (**automate-this**, **test-drive**):** if nothing on hand can fetch or emulate the needed signal, create a clean, secret-safe (**no-leaked-secrets**) script, helper, or project skill. Read-only reviewers place scratch fetchers in their writable repro folder or ask the lead to dispatch a worker for shared repo tooling; publish the path and usage to the lead and peer agents (`LANES.md` / report) for reuse.
  - **Fallback without stalling:** when real data remains unavailable or restricted, build the closest realistic case from code paths, schemas, fixtures, and symptoms, mark it as inferred (**decisions-in-plain-words**), and refine it if real data arrives.
- **Replicate the whole failure environment across the full path:** match the conditions correlated with the failure—beyond isolated arguments or queries—including runtime versions, OS and CPU architecture, memory/CPU/disk/FD pressure, network behavior (latency, loss, resets, protocol/HTTP version), config and flags, load/concurrency, and correlated upstream or downstream systems (illustrative, not exhaustive; match reality first, then strip variables in Section 4).
- **Measure frequency & test `main`:** record the observed failure rate (source, window, sample count) for **prove-it** and flaky bisects. Run the scenario on `main` first: if it behaves, log one line and move on; if `main` already fails, isolate it separately (**leave-it-better**) only when it blocks your work.
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

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `automate-this` (`${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`), `test-drive` (`${CLAUDE_SKILL_DIR}/../test-drive/SKILL.md`), `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `leave-it-better` (`${CLAUDE_SKILL_DIR}/../leave-it-better/SKILL.md`), `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`), `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `challenge` (`${CLAUDE_SKILL_DIR}/../challenge/SKILL.md`), `fix-it` (`${CLAUDE_SKILL_DIR}/../fix-it/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's bug-fix, live-symptom, and profile diagnosis playbooks (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
