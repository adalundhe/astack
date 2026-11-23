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
   Why: left alone, agents expand scope without end.

1. TIME LIMIT, HARD: <worker_minutes> minutes. At <worker_minutes minus wind_down_minutes> minutes, merge what is
   green, push the rest to your branch, report and end. The lead starts your successor from your report.
   Why: the limit keeps each worker on its deliverable, and the report carries the work forward.

2. MERGE GATE: lint what you touched (`<command>`) and test what you touched (`<command>`). When both pass, merge
   to <target> (`<steps>`). If the push is refused, fetch, merge, retest and push again. Never force-push. Full
   suites and benchmarks of the whole are the lead's, on <target>, after merges.
   Why: merged work outlives the worker, and heavy runs from every worker overload shared machines.

3. WHERE: your worktree (<path>), on branch <prefix>/<lane>. Write only the paths your brief names. Builds and
   tests run <where, and with what resources>.
   Why: workers that share a checkout or a build folder overwrite each other.

4. DECIDE YOURSELF: settle questions from the person's earlier decisions, the repository, outside research, and an
   A/B, in that order. Only what none of those settles goes in your report, under NEEDS THE PERSON.
   Why: a question the work can answer shouldn't wait on the person.

5. PROJECT RULES: <the project's own binding rules, or their paths>.
   Why: this program's work meets the same bar as every other change to the project.

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
   Why: others' work isn't yours to stop, and a printed secret is a leaked one.

8. REPORT: your final message is the lane report, losses first.
   Why: the lead plans your successor from what is missing.

## Revisions

<The lead adds each change here with its time and reason, and tells every running worker.>
