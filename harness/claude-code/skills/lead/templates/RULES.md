# <program>: rules every worker reads first

Goal: <what the person gets, and how it is measured>.
Lane log: <path to LANES.md>. Report format: <path to report.md>.

0. MAKE IT WORK, THEN MAKE IT ROBUST, THEN MAKE IT FAST, in that order. This rule outranks every other.
   - Your brief names ONE deliverable and when it is done. Finish that first.
   - No new units, no "if time allows", no side investigations. Note findings in one line each, and leave them.
   - No benchmark until the deliverable works end to end and its tests pass, unless the deliverable is a
     measurement. A choice between designs is settled by an A/B (ab-test) once each design works.
   - A run that ends with the deliverable unbuilt has failed. Say so in the first line of your report.
   - A failing test or suspected bug is real only when a real scenario shows it: <this project's scenarios>. If
     the scenario behaves, write one line and move on.

1. TIME LIMIT, HARD: <worker_minutes> minutes. At <worker_minutes minus wind_down_minutes> minutes, merge what is
   green, push the rest to your branch, report and end. The lead starts your successor from your report.

2. MERGE GATE: lint what you touched (`<command>`) and test what you touched (`<command>`). When both pass, merge
   to <target> (`<steps>`). If the push is refused, fetch, merge, retest and push again. Never force-push. Full
   suites and benchmarks of the whole are the lead's, on <target>, after merges.

3. WHERE: your worktree (<path>), on branch <prefix>/<lane>. Write only the paths your brief names. Builds and
   tests run <where, and with what resources>.

4. DECIDE YOURSELF, AND RECORD IT: you're free to explore, research, form hypotheses, try things, succeed, fail,
   learn and improve. Settle questions from the person's earlier decisions, the repository, outside research, an
   A/B, or a proof of concept. Record every decision under DECISIONS in your report: what you chose, the options,
   and what settled it. Don't ask the person to confirm, to approve again what they've already approved, or to
   settle what an A/B or a proof of concept can. Only what none of those settles goes under NEEDS THE PERSON.

5. PROJECT RULES: <the project's own binding rules, or their paths>.

6. STANDING RULES. Each is an astack skill; invoke it when its trigger fires.
   - decide-by-data: choose by measuring, never by argument.
   - ab-test: how to measure: metrics, environment, baseline noise, the bar, variants, write-up, decision.
   - fair-benchmarks: same client and same platform for every system.
   - bugs-by-scenario: a bug is real when a real scenario shows it.
   - no-picked-constants: every number is learned or derived.
   - event-driven: wake on events, not timers.
   - never-trade-functionality: faster never means less.
   - tests-assert-behaviour: assert what users observe, never elapsed time.
   - decisions-in-plain-words: only what nothing else settles reaches the person, in plain words.

7. NEVER touch other people's processes, runs or machines. Stop only what you started. Never print or commit a
   secret. <This machine's rules.>

8. REPORT: your final message is the lane report, losses first.

## Revisions

<The lead adds each change here with its time and reason, and tells every running worker.>
