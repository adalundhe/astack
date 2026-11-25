---
name: find-it
description: "Debug runtime issues by collecting targeted logs, stdout/stderr captures, screenshots, OTel-traced HTTP/2/3 & distributed traces, Playwright captures, metrics, and profiles saved as <file>_DEBUG_<shorthash>.<type>, preferring built-in language tools, then astack tools, then third-party tools, and cleaning all debug data once fixed. Use when investigating hard-to-see runtime failures, UI/network bugs, flakes, hangs, or slowdowns."
disable-model-invocation: true
---

# Find it

Gather targeted runtime evidence—logs, `stdout`/`stderr`, screenshots, telemetry, metrics, traces, and profiles—to expose what the running system is actually doing, then leave zero trace behind once fixed.

## Tool preference order

Always reach for tools in this order:

1. **Built-in language and runtime debuggers first** (e.g., `pdb`/`faulthandler`/`tracemalloc`/`cProfile` in Python; `go tool pprof`/`go tool trace`/`delve` in Go; `--inspect`/V8 profiler in Node/Bun; `lldb`/`gdb`/`cargo`/sanitizers in Rust/C/C++; `jstack`/`jfr` on JVM; native browser DevTools).
2. **astack tools and skills next** (**diagnose**, **prove-it**, **test-drive** `drive-<app>` flows, **show-the-states** / `astack-statechart`, **benchmarking**, and configured `astack-tools` / `werkflow` helpers).
3. **Third-party tools last**, only when built-in and astack tools don't expose the signal.

## Capture naming rule

Save **every** collected debug artifact as **`<file>_DEBUG_<shorthash>.<type>`** (target module/component name, short 7-char hash of the run/commit, and file extension—e.g., `auth_DEBUG_a1b2c3d.log`, `server_DEBUG_a1b2c3d.stderr`, `checkout_DEBUG_9f0e1d2.png`, `api_DEBUG_4c5d6e7.trace`, `worker_DEBUG_4c5d6e7.prof`, `flow_DEBUG_8e7f6a5.har`). Keep captures untracked so they are trivial to locate, correlate, and clean.

## Signals and tools (helpful starting set, not exhaustive)

1. **Logs & `stdout`/`stderr` capture:** split `stdout` and `stderr` with timestamps and exit codes (`tee`), enable targeted log levels for only the suspect module, and keep correlation/request IDs.
2. **OpenTelemetry (OTel) tracing & HTTP/1.1 / HTTP/2 / HTTP/3 inspection:** enable OTel spans and `traceparent` propagation across services, export to console/OTLP capture, and inspect HTTP/2 & HTTP/3 streams, headers, trailers, and resets (`curl --http2`/`--http3`, proxy captures, `tshark`).
3. **Screenshots & browser/UI captures:** use Playwright (screenshots, trace zips, HAR network logs, console errors) or your repo's **test-drive** `drive-<app>` flow to capture visual regressions, layout breakage, and client-side failures.
4. **Telemetry & metrics:** sample counters, histograms, queue depths, retry/error rates, GC pauses, RSS/heap, and open FDs/sockets across the failure window.
5. **Profiling, live dumps & replay:** capture CPU flamegraphs (`perf`, `py-spy`, `samply`, `pprof`), allocation/lock profiles, thread/goroutine/task stacks, syscall/network probes (`strace`, `lsof`, `tcpdump`), or `rr` traces **before** restarting a stuck process.

## Hygiene and cleanup

1. **Never leak secrets into captures (**no-leaked-secrets**):** redact or exclude tokens, credentials, `Authorization`/`Cookie` headers, and personal data before writing logs, HARs, traces, or screenshots.
2. **Correlate, shrink, and prove (**diagnose**, **prove-it**, **fix-it**):** line up timestamps and trace IDs across captures to test one falsifiable hypothesis at a time; shrink confirmed repros (**prove-it**), revert disproved instrumentation immediately, and apply the minimal fix via **fix-it**.
3. **Clean up during debugging and once fixed (**cleanup**):** prune stale `<file>_DEBUG_<shorthash>.<type>` files mid-investigation as needed, and **always** run **cleanup** once the issue is fixed and verified so every `<file>_DEBUG_<shorthash>.<type>` capture and temporary debug hook is removed.

Referenced skills: `diagnose` (`${CLAUDE_SKILL_DIR}/../diagnose/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `test-drive` (`${CLAUDE_SKILL_DIR}/../test-drive/SKILL.md`), `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`), `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `fix-it` (`${CLAUDE_SKILL_DIR}/../fix-it/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.
