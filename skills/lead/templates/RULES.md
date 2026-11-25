# <program>: rules every worker reads first

Goal: <what the person gets, and how it is measured>.
Lane log: <path to LANES.md>. Report format: <path to report.md>.
Astack skills: <path to astack skills/ directory, for reading hidden skills by path>.

0. MAKE IT WORK, THEN MAKE IT ROBUST, THEN MAKE IT FAST, in that order. This rule outranks every other.
   - **The bar in your brief is the whole bar.** Your brief names ONE deliverable and when it is done. Finish that first.
   - No new units, no unasked extra gates, no "if time allows", no side investigations. Note findings in one line each, and leave them.
   - Never weaken, skip, or game a gate (no relaxed assertions, muted lints, or filtered-out failing tests). If a gate itself is wrong, stop and report it with evidence; only a lead-countersigned entry in `## Revisions` changes a gate, and broken gates are fixed in their own dedicated change.
   - No benchmark until the deliverable works end to end and its tests pass, unless the deliverable is a
     measurement. A choice between designs is settled by an A/B (ab-test) once each design works.
   - A run that ends with the deliverable unbuilt has failed. Say so in the first line of your report.
   - A failing test or suspected bug is real only when a real scenario shows it: <this project's scenarios>. If
     the scenario behaves, write one line and move on.

1. TIME LIMITS, HARD:
   - Workers: <worker_minutes> minutes (wind down at <worker_minutes minus wind_down_minutes>m: merge what is green, push the rest, report and end; the lead starts your successor from your report).
   - Reviewers: <reviewer_minutes> minutes (wind down at <reviewer_minutes minus wind_down_minutes>m: finalize verified findings, list unfinished areas under `COULD NOT TEST`, report and end).
   - Researchers: <researcher_minutes> minutes (wind down at <researcher_minutes minus wind_down_minutes>m: finalize verified citations, list unfinished lookups under `COULD NOT ACCESS`, report and end).

2. MERGE GATE (every lane clears lead review; test scope and reviewer count scale to change risk):
   - Low-risk, isolated edits: lint what you touched (`<command>`), test what you touched (`<command>`), and clear lead vectored review (1 non-worker reviewer when `reviewer_pool` allows) before landing; full suites and whole-system benchmarks run on `<target>` after merges.
   - Medium/high-risk changes (shared interfaces, concurrency, persistence, security, or large diffs): run the broader/full suite (`<command>`) and clear lead vectored review (>=2 blind reviewers on different models per risky vector) before landing on `<target>`.
   - Rebase or merge `<target>` only when `<target>` moved since you branched (so untested code would otherwise land). After rebasing, run `astack-watch-pr patch-id-check --before <old_base>..<old_head> --after <new_base>..HEAD --json` (checks both `git patch-id` and `git range-diff` to ensure no behavior was dropped or resurrected); carry the prior verdict only when `carry_verdict` is `true` and incoming `<target>` commits do not overlap your blast radius—otherwise retest the combined tree. Never force-push shared/protected branches.
   - Takeover credit: when finishing or squashing another person's commits/PR, preserve original git authorship or add `Co-authored-by: Name <email>` trailers (`astack-watch-pr authorship-check`).
   - Autonomy grant (from `settings.json`): mode `<supervised|unattended>`, allow `<list>`, deny `<list>`. Never take any action in `deny` without explicit per-action approval.
   - No worker may loosen a gate unilaterally—every gate relaxation requires the lead's countersign in `## Revisions`.

3. WHERE: your isolated Slates in-memory VFS volume (`slates`, https://github.com/hyper-light/slates, preferred when available) or git worktree (<path>), on branch <prefix>/<lane>. Write only the paths your brief names. Builds and
   tests run <where, and with what resources>.

4. DECIDE YOURSELF, AND RECORD IT: you're free to explore, research, form hypotheses, try things, succeed, fail,
   learn and improve. Settle questions from the person's earlier decisions, the repository, outside research, an
   A/B, or a proof of concept. Record every decision under DECISIONS in your report: what you chose, the options,
   and what settled it. Don't ask the person to confirm, to approve again what they've already approved, or to
   settle what an A/B or a proof of concept can. Only what none of those settles goes under NEEDS THE PERSON.

5. PROJECT RULES: <the project's own binding rules, or their paths>.

6. STANDING RULES. Each is a hidden astack skill; read its `SKILL.md` from the Astack skills folder above whenever its trigger fires.
   - decide-by-data: choose by measuring, never by argument.
   - ab-test: how to measure: metrics, environment, baseline noise, the bar, variants, write-up, decision.
   - baseline: same client and same platform for every system.
   - find-it: confirm bugs on real user scenarios, narrow root causes with runtime evidence/bisect/profiles, shrink repros, and revert disproved hypotheses.
   - fix-it: apply minimal, behavior-proven root-cause fixes without state/lock hacks or out-of-scope refactors.
   - no-picked-constants: every number is learned or derived.
   - event-driven: wake on events, not timers.
   - never-trade-functionality: faster never means less.
   - tests-assert-behaviour: assert what users observe, never elapsed time.
   - decisions-in-plain-words: only what nothing else settles reaches the person, in plain words.

7. NEVER touch other people's processes, runs or machines. Stop only what you started. Never print or commit a
   secret. <This machine's rules.>

8. REPORT: your final message is the lane report, losses first.

## Revisions

<The lead adds each change here—and countersigns any gate relaxation—with its time, reason, and evidence, and tells every running worker.>
