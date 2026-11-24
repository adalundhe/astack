---
name: diagnose
description: "Find the root cause of a bug, live runtime symptom, or profile anomaly using binary search with runtime evidence, live state dumps, profile attribution, and clean reverts of disproved hypotheses. Use once a failure is confirmed or when investigating live hangs, leaks, or slowdowns."
---

# Diagnose

Narrow a confirmed bug, live symptom, or performance anomaly down to its root cause with runtime evidence—reverting anything a disproved hypothesis motivated.

1. **Confirm the symptom first** (**bugs-by-scenario**): capture the exact user-observable failure (error, wrong output, hang, leak, latency cliff) and a repeatable repro command; check whether `main` already exhibits it.
2. **Pick the investigation method for the symptom:**
   - **Code or behavioral bug (wrong output, crash, regression):** narrow by **binary search with runtime evidence**—across history (`git bisect run` against the repro) or across execution space (inspect state at the midpoint between input boundary and failure, cutting the suspect region in half each step). One discriminating observation beats five guesses.
   - **Live runtime symptoms (hangs, deadlocks, memory leaks, CPU pegs, FD/socket exhaustion, flapping):** capture diagnostic state **before** restarting or killing anything—stack/thread/goroutine/task dumps, lock/wait graphs, open FDs/sockets, process tree, heap/RSS growth samples, and structured logs/traces. Diagram the stuck or unexpected transition if state-dependent (**show-the-states**).
   - **Captured profiles and traces (CPU flamegraphs, allocation profiles, lock contention, query/I/O plans):** read top-down from the user-visible hot path, separate waiting (locks, I/O, GC, scheduling) from CPU work, map every hot frame to `file:line`, and confirm the profile window covers the slow event (**benchmarking**).
3. **Test one falsifiable hypothesis at a time:**
   - State the hypothesis, mechanism, and the exact observation that would disprove it before touching code.
   - **Revert disproved hypotheses immediately:** if the evidence refutes a hypothesis, roll back every edit, flag, or workaround it motivated before trying the next one. Never leave speculative changes stacked in the tree.
   - If two consecutive fixes miss or the mechanism feels shaky, stop and interrogate the diagnosis (**challenge**).
4. **Prove the root cause and fix cleanly:**
   - Write a failing test capturing the exact root-cause mechanism (**tests-assert-behaviour**).
   - Check indirect callers and invariants (**blast-radius**), apply the minimal fix, and verify both the new test and original user scenario pass (**prove-it**).
   - Report the symptom, bisect/evidence trail, disproved hypotheses reverted, root cause (`file:line`), and regression test.

Referenced skills: `bugs-by-scenario` (`../bugs-by-scenario/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`), `challenge` (`../challenge/SKILL.md`), `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's bug-fix, live-symptom, and profile diagnosis playbooks (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
