# <program>: rules every lane reads first

Goal: <what the person gets when the program is done, and how it is measured>.
Lead: <the lead's session>. Lane log: <absolute path to LANES.md>. Report format: <absolute path to report.md>.

0. MAKE IT WORK, THEN MAKE IT ROBUST, THEN MAKE IT FAST, in that order. This rule outranks every other.
   - Your brief names ONE deliverable and the point at which it is done. Finish that before anything else.
   - No new units. No "if time allows". No side investigations. Note anything you find on the way in your
     report, one line each, and leave it.
   - No benchmark or A/B until the deliverable works end to end and its tests pass. The only exception is
     a brief whose deliverable is itself a measurement.
   - An hour that ends with the deliverable unbuilt is a failed hour. Say so in the first line of your report.
   - A failing test or a suspected bug is real when a real scenario shows it: <this project's scenarios: the
     queries, workloads and competitor benchmarks a user would run>, run the way a user runs them. If the
     scenario behaves, write one line about it and move on.
   Why: left alone, agents expand scope without end. A complete implementation comes first, a robust one
   second, a fast one third.

1. ONE HOUR, HARD. At 55 minutes, merge what is green, push the rest to your branch, write your report and
   end. The lead starts your successor from your report.
   Why: the hour keeps each lane on its deliverable, and the report is how the work outlives the lane.

2. MERGE GATE. Lint what you touched: `<lint command>`. Test what you touched: `<test command>`. When both
   pass, merge to <target>: `<merge and push steps>`. If the push is refused because <target> moved, fetch,
   merge, re-test the touched parts and push again. Never force-push. Commit per step, with the evidence in
   the message. Full suites, end-to-end runs and benchmarks of the whole run on <target> after the merge;
   they are the lead's.
   Why: green work merged at once outlives the lane, and heavy runs from every lane overload shared machines.

3. WHERE YOU WORK. Your own clone or worktree at <path pattern>, on branch <prefix>/<area>. Write only the
   paths your brief names. Builds and tests run <where, and with the resources a run may take>.
   Why: lanes that share a checkout or a build folder overwrite each other's work.

4. THIS PROJECT'S RULES. <Its CLAUDE.md or AGENTS.md rules that bind every change, or their paths.>
   Why: a program's lanes are held to the same bar as any other change to the project.

5. STANDING RULES. Each has an astack skill. Invoke it when its trigger fires.
   a. Decide by data. Build both designs, A/B them at the extremes, force their failure modes, and let the
      numbers choose. (decide-by-data)
   b. Fair benchmarks. The same client and the same platform for every system compared. (fair-benchmarks)
   c. No picked constants. Every limit, size, threshold or interval is learned where it runs or derived
      from a cited source. (no-picked-constants)
   d. Event-driven, not timers. Wake on the event; use time only for real deadlines. (event-driven)
   e. Never trade functionality, correctness or durability for speed. If a gain needs that, stop and report
      it as a decision with numbers; don't land it. (never-trade-functionality)
   f. Tests assert behaviour, never elapsed time. (tests-assert-behaviour)
   g. Plain words to the person. Decisions go in your report as plain choices with a recommendation.
      (decisions-in-plain-words)
   Why: each rule is in its skill, beside the rule.

6. NEVER restart or touch other people's processes, runs or machines. Stop only runs you started. Never
   print or commit a secret. <This machine's rules: where big files go, what must not run here.>
   Why: other work on the machine isn't yours to stop, and a printed secret is a leaked one.

7. REPORT. Your final message is the lane report (<absolute path to report.md>), losses first.
   Why: the lead plans your successor from what is missing, so that comes first.

## Revisions

The lead appends each change here, with its time from `date -u +%H:%MZ` and its reason, and tells every
running lane.

<HH:MMZ> <what changed, and why>
